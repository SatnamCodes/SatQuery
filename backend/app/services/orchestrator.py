"""Agentic controller: classifies a natural-language question + attached
imagery into one of a fixed set of tools, validates the request against
each tool's input requirements, degrades gracefully to VQA when the
request doesn't fit, executes the chosen tool, and returns a uniform
result plus an ExecutionTrace for auditability.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from PIL import Image

from . import change_detection, fusion, grounding, segmentation
from .vlm import vlm

# --- Tool registry -----------------------------------------------------
# min_images / max_images: how many images the tool needs.
# pair_type: None (no constraint), "bi_temporal" (same modality, two dates),
#            or "cross_modal" (one optical + one sar).
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "vqa": {
        "description": "Answer a free-form question about the image(s) using the VLM.",
        "min_images": 1,
        "max_images": 2,
        "pair_type": None,
    },
    "caption": {
        "description": "Describe/summarize the scene in a single image.",
        "min_images": 1,
        "max_images": 1,
        "pair_type": None,
    },
    "grounding": {
        "description": "Locate a named feature (water, vegetation, built-up) in a single image.",
        "min_images": 1,
        "max_images": 1,
        "pair_type": None,
    },
    "change_detection": {
        "description": "Compare two same-modality images of the same scene taken at different times.",
        "min_images": 2,
        "max_images": 2,
        "pair_type": "bi_temporal",
    },
    "optical_sar_fusion": {
        "description": "Fuse one optical and one SAR image for higher-confidence land-cover flags.",
        "min_images": 2,
        "max_images": 2,
        "pair_type": "cross_modal",
    },
}

CHANGE_KEYWORDS = ["change", "differ", "compare", "before and after", "appeared", "disappeared", "new construction", "what changed"]
FUSION_KEYWORDS = ["fusion", "sar", "radar", "confidence", "cross-modal", "cross modal", "backscatter"]
GROUNDING_KEYWORDS = ["where", "locate", "find", "point out", "show me", "which part"]
CAPTION_KEYWORDS = ["describe", "caption", "summarize", "summarise", "what is in this image", "what's in this image"]


@dataclass
class ExecutionTrace:
    task: str
    tools: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    input_check: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "tools": self.tools,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "input_check": self.input_check,
        }


def _classify(question: str, n_images: int, pair_type: Optional[str]) -> str:
    q = question.lower()

    if n_images >= 2 and pair_type == "cross_modal" and any(k in q for k in FUSION_KEYWORDS):
        return "optical_sar_fusion"
    if n_images >= 2 and pair_type == "bi_temporal" and any(k in q for k in CHANGE_KEYWORDS):
        return "change_detection"
    # Even without the exact pair_type, strong intent keywords still pick the task;
    # validation below will decide whether to degrade to VQA.
    if any(k in q for k in FUSION_KEYWORDS):
        return "optical_sar_fusion"
    if any(k in q for k in CHANGE_KEYWORDS):
        return "change_detection"
    if any(k in q for k in GROUNDING_KEYWORDS):
        return "grounding"
    if any(k in q for k in CAPTION_KEYWORDS):
        return "caption"
    return "vqa"


def _validate(task: str, n_images: int, pair_type: Optional[str]) -> Dict[str, Any]:
    spec = TOOL_REGISTRY[task]
    checks = {
        "min_images_required": spec["min_images"],
        "max_images_required": spec["max_images"],
        "images_provided": n_images,
        "pair_type_required": spec["pair_type"],
        "pair_type_provided": pair_type,
    }
    ok = spec["min_images"] <= n_images <= spec["max_images"]
    if spec["pair_type"] is not None:
        ok = ok and pair_type == spec["pair_type"]
    checks["passed"] = ok
    return checks


def route(
    question: str,
    images: List[Image.Image],
    modalities: Optional[List[str]] = None,
    pair_type: Optional[str] = None,
) -> Dict[str, Any]:
    modalities = modalities or []
    n_images = len(images)

    requested_task = _classify(question, n_images, pair_type)
    input_check = _validate(requested_task, n_images, pair_type)

    task = requested_task
    degraded = False
    if not input_check["passed"] and requested_task != "vqa":
        degraded = True
        # Grounding/caption just need >=1 image; if we have that, keep them.
        if requested_task in ("grounding", "caption") and n_images >= 1:
            task = requested_task
            degraded = False
            input_check = _validate(task, n_images, pair_type)
        else:
            task = "vqa"
            input_check = _validate(task, min(n_images, TOOL_REGISTRY["vqa"]["max_images"]), pair_type)

    trace = ExecutionTrace(task=task, input_check=input_check)
    trace.parameters = {"question": question, "n_images": n_images, "modalities": modalities, "pair_type": pair_type}
    if degraded:
        trace.parameters["degraded_from"] = requested_task

    result = _execute(task, question, images, trace)
    result["execution_trace"] = trace.to_dict()
    return result


def _execute(task: str, question: str, images: List[Image.Image], trace: ExecutionTrace) -> Dict[str, Any]:
    if task == "change_detection":
        trace.tools = ["change_detection"]
        trace.confidence = 0.9
        stats = change_detection.detect_change(images[0], images[1])
        answer = vlm.narrate_change(question, stats)
        return {"task": task, "answer": answer, "stats": stats, "overlay_png_base64": stats["overlay_png_base64"]}

    if task == "optical_sar_fusion":
        trace.tools = ["optical_sar_fusion"]
        trace.confidence = 0.85
        stats = fusion.fuse(images[0], images[1])
        answer = vlm.narrate_fusion(question, stats)
        return {"task": task, "answer": answer, "stats": stats, "overlay_png_base64": stats["overlay_png_base64"]}

    if task == "grounding":
        trace.tools = ["grounding"]
        result = grounding.ground(images[0], question)
        trace.confidence = 0.8 if result["matched"] else 0.3
        trace.parameters["resolved_category"] = result["category"]
        answer = vlm.ask(question, [images[0]], context={"grounding_result": {k: v for k, v in result.items() if k != "overlay_png_base64"}})
        return {"task": task, "answer": answer, "stats": result, "overlay_png_base64": result["overlay_png_base64"]}

    if task == "caption":
        trace.tools = ["segmentation", "vqa"]
        trace.confidence = 0.7
        seg = segmentation.segment(images[0])
        context = {"coverage_percent": seg["coverage_percent"]}
        answer = vlm.ask(question or "Describe this scene.", [images[0]], context=context)
        return {"task": task, "answer": answer, "stats": seg, "overlay_png_base64": seg["overlay_png_base64"]}

    # default: vqa
    trace.tools = ["vqa"]
    trace.confidence = 0.6
    answer = vlm.ask(question, images[: TOOL_REGISTRY["vqa"]["max_images"]] if images else None)
    return {"task": "vqa", "answer": answer, "stats": None, "overlay_png_base64": None}
