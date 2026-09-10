"""Visual grounding: map a free-text target phrase to a segmentation
category via keyword matching, then localize the largest matching region.
"""
from typing import Any, Dict, Optional

import cv2
import numpy as np
from PIL import Image

from .imgutils import bgr_to_base64_png, pil_to_bgr
from .segmentation import get_masks

KEYWORD_MAP = {
    "water": ["water", "lake", "river", "pond", "reservoir", "flood", "sea", "stream", "canal"],
    "vegetation": ["vegetation", "forest", "tree", "crop", "field", "farmland", "green", "plant", "agricult"],
    "built_up": ["building", "built", "construction", "urban", "road", "house", "structure", "settlement", "infrastructure"],
}

BOX_COLOR = (0, 191, 255)  # amber


def resolve_category(target_phrase: str) -> Optional[str]:
    phrase = target_phrase.lower()
    for category, keywords in KEYWORD_MAP.items():
        if any(kw in phrase for kw in keywords):
            return category
    return None


def ground(image: Image.Image, target_phrase: str) -> Dict[str, Any]:
    category = resolve_category(target_phrase)
    bgr = pil_to_bgr(image)
    h, w = bgr.shape[:2]

    if category is None:
        return {
            "matched": False,
            "category": None,
            "bbox": None,
            "overlay_png_base64": bgr_to_base64_png(bgr),
            "image_size": {"width": w, "height": h},
            "message": f"Could not map '{target_phrase}' to a known category (water, vegetation, built_up).",
        }

    masks = get_masks(image)
    mask = masks[category]
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    overlay = bgr.copy()
    if not contours:
        return {
            "matched": False,
            "category": category,
            "bbox": None,
            "overlay_png_base64": bgr_to_base64_png(overlay),
            "image_size": {"width": w, "height": h},
            "message": f"'{target_phrase}' mapped to category '{category}' but no matching region was found in this image.",
        }

    largest = max(contours, key=cv2.contourArea)
    x, y, cw, ch = cv2.boundingRect(largest)
    bbox = {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch), "area_px": int(cv2.contourArea(largest))}

    cv2.rectangle(overlay, (x, y), (x + cw, y + ch), BOX_COLOR, 3)

    return {
        "matched": True,
        "category": category,
        "bbox": bbox,
        "overlay_png_base64": bgr_to_base64_png(overlay),
        "image_size": {"width": w, "height": h},
        "message": f"'{target_phrase}' mapped to category '{category}'.",
    }
