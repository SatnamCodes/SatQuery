"""Thin wrapper around google-generativeai for the remote-sensing VLM
persona used to narrate results and answer free-form visual questions.

Rule for every narration method: only describe numbers that were actually
measured upstream (change %, coverage %, region counts, etc.) — never
invent statistics. The system prompt below reinforces this instruction to
the model itself.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from PIL import Image

DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"
load_dotenv(DATA_ROOT.parent / ".env")


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


MODEL_NAME = "gemini-3.6-flash"


class GeminiVLM:
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

    def _not_configured_message(self) -> str:
        return (
            "SatQuery's narration model (Gemini) is not configured on this server. "
            "Set the GEMINI_API_KEY environment variable to enable natural-language answers. "
            "Raw measurements are still available in the response."
        )

    def _generate(self, contents: List[Any]) -> str:
        from google.genai import types

        response = self._client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        return response.text.strip()

    def ask(self, question: str, images: Optional[List[Image.Image]] = None, context: Optional[Dict[str, Any]] = None) -> str:
        if not self.configured:
            return self._not_configured_message()
        try:
            parts: List[Any] = []
            if context:
                parts.append(f"Measured data: {context}")
            parts.append(f"Question: {question}")
            if images:
                parts.extend(images)
            return self._generate(parts)
        except Exception as exc:
            return f"VLM request failed: {exc}"

    def narrate_change(self, question: str, stats: Dict[str, Any]) -> str:
        if not self.configured:
            return self._not_configured_message()
        try:
            prompt = (
                f"Question: {question}\n"
                f"Measured data: change_percent={stats.get('change_percent')}, "
                f"region_count={stats.get('region_count')}, bboxes={stats.get('bboxes')}\n"
                "Narrate this change-detection result for a field officer, using only these numbers."
            )
            return self._generate([prompt])
        except Exception as exc:
            return f"VLM request failed: {exc}"

    def narrate_fusion(self, question: str, stats: Dict[str, Any]) -> str:
        if not self.configured:
            return self._not_configured_message()
        try:
            prompt = (
                f"Question: {question}\n"
                f"Measured data: {stats}\n"
                "Narrate this optical+SAR fusion result for a field officer, using only these numbers. "
                "Explain the difference between 'high_confidence' (both sensors agree) and 'possible' "
                "(only one sensor flags it)."
            )
            return self._generate([prompt])
        except Exception as exc:
            return f"VLM request failed: {exc}"


vlm = GeminiVLM()
