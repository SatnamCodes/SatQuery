"""HSV-heuristic land-cover segmentation for a single optical image.

No trained model is required: water, vegetation, and built-up/bare-soil
areas each occupy fairly distinct hue/saturation/value bands in typical
RGB satellite chips, so simple HSV thresholds give a fast, explainable
first pass suitable for a field-officer triage tool.
"""
from typing import Any, Dict

import cv2
import numpy as np
from PIL import Image

from .imgutils import bgr_to_base64_png, pil_to_bgr

# BGR overlay colors per category
COLORS = {
    "water": (255, 128, 0),      # blue-ish
    "vegetation": (0, 200, 0),   # green
    "built_up": (0, 0, 230),     # red
}


def _water_mask(hsv: np.ndarray) -> np.ndarray:
    lower = np.array([85, 40, 30])
    upper = np.array([140, 255, 255])
    return cv2.inRange(hsv, lower, upper)


def _vegetation_mask(hsv: np.ndarray) -> np.ndarray:
    lower = np.array([30, 40, 30])
    upper = np.array([85, 255, 255])
    return cv2.inRange(hsv, lower, upper)


def _built_up_mask(hsv: np.ndarray, water: np.ndarray, veg: np.ndarray) -> np.ndarray:
    # Built-up / bare soil: low saturation, mid-to-high value, not water/veg.
    lower = np.array([0, 0, 90])
    upper = np.array([179, 60, 255])
    candidate = cv2.inRange(hsv, lower, upper)
    exclude = cv2.bitwise_or(water, veg)
    return cv2.bitwise_and(candidate, cv2.bitwise_not(exclude))


def segment(image: Image.Image) -> Dict[str, Any]:
    bgr = pil_to_bgr(image)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    water = _water_mask(hsv)
    water = cv2.morphologyEx(water, cv2.MORPH_OPEN, kernel)

    veg = _vegetation_mask(hsv)
    veg = cv2.morphologyEx(veg, cv2.MORPH_OPEN, kernel)

    built = _built_up_mask(hsv, water, veg)
    built = cv2.morphologyEx(built, cv2.MORPH_OPEN, kernel)

    total_px = bgr.shape[0] * bgr.shape[1]
    coverage = {
        "water": round(100.0 * np.count_nonzero(water) / total_px, 3),
        "vegetation": round(100.0 * np.count_nonzero(veg) / total_px, 3),
        "built_up": round(100.0 * np.count_nonzero(built) / total_px, 3),
    }

    overlay = bgr.copy()
    masks = {"water": water, "vegetation": veg, "built_up": built}
    for name, mask in masks.items():
        color_layer = np.zeros_like(overlay)
        color_layer[:, :] = COLORS[name]
        m = mask.astype(bool)
        overlay[m] = cv2.addWeighted(overlay, 0.5, color_layer, 0.5, 0)[m]

    return {
        "coverage_percent": coverage,
        "overlay_png_base64": bgr_to_base64_png(overlay),
        "image_size": {"width": bgr.shape[1], "height": bgr.shape[0]},
    }


def get_masks(image: Image.Image) -> Dict[str, np.ndarray]:
    """Return raw binary masks (for reuse by fusion/grounding). Not part of the public API response."""
    bgr = pil_to_bgr(image)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    water = cv2.morphologyEx(_water_mask(hsv), cv2.MORPH_OPEN, kernel)
    veg = cv2.morphologyEx(_vegetation_mask(hsv), cv2.MORPH_OPEN, kernel)
    built = cv2.morphologyEx(_built_up_mask(hsv, water, veg), cv2.MORPH_OPEN, kernel)

    return {"water": water, "vegetation": veg, "built_up": built}
