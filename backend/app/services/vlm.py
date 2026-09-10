"""VLM wrapper with two interchangeable backends:

  - Gemini (cloud): used in the deployed environment. Needs GEMINI_API_KEY.
  - Ollama (local): used for local dev against a GPU, no API key, no rate
    limit, no cost. Needs a local Ollama server with a vision model pulled
    (default: qwen2.5vl:7b).

Selection is via SATQUERY_VLM_BACKEND=gemini|ollama|auto (default "auto":
prefer Gemini if GEMINI_API_KEY is set, else fall back to Ollama).

When the Gemini backend hits its rate limit, callers get a message telling
them to run SatQuery locally and switch to the Ollama backend, rather than
a raw API error — the deployed demo shouldn't dead-end when the free tier
is exhausted.

Rule for every narration method: only describe numbers that were actually
measured upstream (change %, coverage %, region counts, etc.) — never
invent statistics. The system prompt below reinforces this instruction to
the model itself.
"""
import base64
import json
import os
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from PIL import Image

DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"
load_dotenv(DATA_ROOT.parent / ".env")

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL_NAME = os.environ.get("SATQUERY_VLM_MODEL", "qwen2.5vl:7b")
GEMINI_MODEL_NAME = os.environ.get("SATQUERY_GEMINI_MODEL", "gemini-3.6-flash")
BACKEND_CHOICE = os.environ.get("SATQUERY_VLM_BACKEND", "auto")
REQUEST_TIMEOUT_S = 180  # local 7B multimodal inference on a laptop GPU can be slow


class RateLimitError(Exception):
    pass


def _load_domain_fewshot() -> str:
    """Pull 3-5 worked Q/A exemplars straight from the real VRSBench and
    RSVQA sample data fetched by scripts/fetch_data.py, so the domain
    few-shot grounding is backed by actual benchmark annotations rather
    than hand-written examples. Falls back to a short note if the sample
    data hasn't been fetched yet (fetch_data.py wasn't run)."""
    examples = []

    vrsbench_path = DATA_ROOT / "vrsbench_sample" / "manifest.json"
    if vrsbench_path.exists():
        entries = json.loads(vrsbench_path.read_text())
        for entry in entries:
            qa = (entry.get("qa_pairs") or [None])[0]
            if qa and qa.get("question") and qa.get("answer"):
                examples.append((qa["question"], qa["answer"], "VRSBench"))
            if len(examples) >= 3:
                break

    rsvqa_path = DATA_ROOT / "rsvqa_sample" / "manifest.json"
    if rsvqa_path.exists():
        entries = json.loads(rsvqa_path.read_text())
        for entry in entries:
            qa = (entry.get("qa_pairs") or [None])[0]
            if qa and qa.get("question") and qa.get("answer"):
                examples.append((qa["question"], qa["answer"], "RSVQA-LR"))
            if len(examples) >= 5:
                break

    if not examples:
        return (
            "(Domain few-shot examples unavailable: run "
            "backend/scripts/fetch_data.py to pull real VRSBench/RSVQA "
            "sample data and populate this section.)"
        )

    lines = [
        "Domain few-shot examples (real question/answer pairs sourced from the "
        "VRSBench and RSVQA-LR benchmark datasets — these ground you in how "
        "remote-sensing questions are phrased and answered, independent of "
        "SatQuery's own measured-data narration examples below):",
    ]
    for i, (q, a, src) in enumerate(examples, 1):
        lines.append(f"[{src}] Q: {q}\nA: {a}")
    return "\n\n".join(lines)


SYSTEM_PROMPT = """You are SatQuery, a remote-sensing analysis assistant embedded in a
field-support tool for satellite/aerial imagery. Your users are field officers without
GIS training who need fast, trustworthy, plain-language answers.

Rules:
- You are given MEASURED statistics (change %, coverage %, region counts, bounding boxes,
  confidence tiers) computed by deterministic image-processing tools. Only report numbers
  that appear in the provided data. NEVER invent, estimate, or round statistics that were
  not given to you.
- If asked a question the provided data cannot answer, say so plainly instead of guessing.
- Keep answers concise, actionable, and free of GIS jargon a field officer wouldn't know.
- Always mention units (%, number of regions, etc.) so answers are unambiguous.

Example 1
Q: What changed between these two images?
Measured data: change_percent=12.4, region_count=3
A: About 12% of this area changed between the two dates, spread across 3 distinct regions.
Take a look at the amber-boxed areas on the overlay for exact locations.

Example 2
Q: Is there a lake in this image?
Measured data: category=water, matched=true, bbox={x:40,y:55,width:120,height:80}
A: Yes — a water body is visible, outlined in the overlay near the center-left of the image
(roughly 120x80 px in size).

Example 3
Q: How confident are you there's new construction?
Measured data: built_up.high_confidence_percent=4.2, built_up.possible_percent=6.8
A: About 4.2% of the area shows built-up signal confirmed by both optical and radar data
(high confidence), with another 6.8% flagged by only one source (worth a field check).

__DOMAIN_FEWSHOT__
"""
SYSTEM_PROMPT = SYSTEM_PROMPT.replace("__DOMAIN_FEWSHOT__", _load_domain_fewshot())


def _image_to_b64(image: Image.Image) -> str:
    buf = BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


# --------------------------------------------------------------------------
# Gemini backend (cloud)
# --------------------------------------------------------------------------
class GeminiBackend:
    name = "gemini"

    def __init__(self) -> None:
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self._client = None
        self.configured = False
        if self.api_key:
            try:
                from google import genai

                self._client = genai.Client(api_key=self.api_key)
                self.configured = True
            except Exception:
                self.configured = False
                self._client = None

    def _generate(self, contents: List[Any]) -> str:
        from google.genai import errors, types

        try:
            response = self._client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
        except errors.ClientError as exc:
            message = str(exc)
            if getattr(exc, "code", None) == 429 or "RESOURCE_EXHAUSTED" in message or "rate limit" in message.lower():
                raise RateLimitError(message) from exc
            raise
        return response.text.strip()

    def ask(self, question: str, images: Optional[List[Image.Image]], context: Optional[Dict[str, Any]]) -> str:
        parts: List[Any] = []
        if context:
            parts.append(f"Measured data: {context}")
        parts.append(f"Question: {question}")
        if images:
            parts.extend(images)
        return self._generate(parts)

    def narrate_change(self, question: str, stats: Dict[str, Any]) -> str:
        prompt = (
            f"Question: {question}\n"
            f"Measured data: change_percent={stats.get('change_percent')}, "
            f"region_count={stats.get('region_count')}, bboxes={stats.get('bboxes')}\n"
            "Narrate this change-detection result for a field officer, using only these numbers."
        )
        return self._generate([prompt])

    def narrate_fusion(self, question: str, stats: Dict[str, Any]) -> str:
        prompt = (
            f"Question: {question}\n"
            f"Measured data: {stats}\n"
            "Narrate this optical+SAR fusion result for a field officer, using only these numbers. "
            "Explain the difference between 'high_confidence' (both sensors agree) and 'possible' "
            "(only one sensor flags it)."
        )
        return self._generate([prompt])


# --------------------------------------------------------------------------
# Ollama backend (local)
# --------------------------------------------------------------------------
class OllamaBackend:
    name = "ollama"

    def __init__(self) -> None:
        self.configured = False
        self._unavailable_reason = None
        try:
            resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            if any(m.split(":")[0] == OLLAMA_MODEL_NAME.split(":")[0] for m in models):
                self.configured = True
            else:
                self._unavailable_reason = (
                    f"Ollama is running but '{OLLAMA_MODEL_NAME}' isn't pulled yet "
                    f"(run: ollama pull {OLLAMA_MODEL_NAME}). Available: {models}"
                )
        except Exception as exc:
            self._unavailable_reason = f"Ollama not reachable at {OLLAMA_BASE_URL} ({exc})"

    def _generate(self, prompt: str, images: Optional[List[Image.Image]] = None) -> str:
        message: Dict[str, Any] = {"role": "user", "content": prompt}
        if images:
            message["images"] = [_image_to_b64(img) for img in images]

        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL_NAME,
                "messages": [{"role": "system", "content": SYSTEM_PROMPT}, message],
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    def ask(self, question: str, images: Optional[List[Image.Image]], context: Optional[Dict[str, Any]]) -> str:
        prompt = f"Measured data: {context}\nQuestion: {question}" if context else f"Question: {question}"
        return self._generate(prompt, images)

    def narrate_change(self, question: str, stats: Dict[str, Any]) -> str:
        prompt = (
            f"Question: {question}\n"
            f"Measured data: change_percent={stats.get('change_percent')}, "
            f"region_count={stats.get('region_count')}, bboxes={stats.get('bboxes')}\n"
            "Narrate this change-detection result for a field officer, using only these numbers."
        )
        return self._generate(prompt)

    def narrate_fusion(self, question: str, stats: Dict[str, Any]) -> str:
        prompt = (
            f"Question: {question}\n"
            f"Measured data: {stats}\n"
            "Narrate this optical+SAR fusion result for a field officer, using only these numbers. "
            "Explain the difference between 'high_confidence' (both sensors agree) and 'possible' "
            "(only one sensor flags it)."
        )
        return self._generate(prompt)


# --------------------------------------------------------------------------
# Router: picks a backend, and turns a Gemini rate-limit into actionable
# guidance instead of a dead-end error.
# --------------------------------------------------------------------------
class VLM:
    def __init__(self) -> None:
        self.gemini = GeminiBackend()
        self.ollama = OllamaBackend()

        if BACKEND_CHOICE == "gemini":
            self.active = self.gemini
        elif BACKEND_CHOICE == "ollama":
            self.active = self.ollama
        else:
            self.active = self.gemini if self.gemini.configured else self.ollama

        self.configured = self.active.configured
        self.backend_name = self.active.name if self.configured else None

    def _not_configured_message(self) -> str:
        if self.active is self.gemini:
            reason = "GEMINI_API_KEY is not set." if not self.gemini.api_key else "Gemini client failed to initialize."
        else:
            reason = self.ollama._unavailable_reason or "Ollama is not reachable."
        return (
            f"SatQuery's narration model is not available ({self.active.name}): {reason} "
            "Raw measurements are still available in the response."
        )

    def _rate_limited_message(self) -> str:
        return (
            "Gemini's free-tier rate limit has been reached for this deployment. "
            "Run SatQuery locally (see backend/README) and set SATQUERY_VLM_BACKEND=ollama "
            "with a local Ollama server + qwen2.5vl:7b pulled to keep using narration for free, "
            "with no rate limit. Raw measurements are still available in the response."
        )

    def _call(self, method: str, *args) -> str:
        if not self.configured:
            return self._not_configured_message()
        try:
            return getattr(self.active, method)(*args)
        except RateLimitError:
            return self._rate_limited_message()
        except Exception as exc:
            return f"VLM request failed: {exc}"

    def ask(self, question: str, images: Optional[List[Image.Image]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        return self._call("ask", question, images, context)

    def narrate_change(self, question: str, stats: Dict[str, Any]) -> str:
        return self._call("narrate_change", question, stats)

    def narrate_fusion(self, question: str, stats: Dict[str, Any]) -> str:
        return self._call("narrate_fusion", question, stats)


vlm = VLM()
