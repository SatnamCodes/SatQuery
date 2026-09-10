"""RGB-channel-relationship land-cover segmentation for a single optical
image.

Earlier versions of this module used fixed HSV hue bands (e.g. "green" =
hue 30-85). That works on punchy, well-saturated photos but falls apart on
real Sentinel-2 imagery: measured against BigEarthNet/EuroSAT samples,
mean saturation was ~29/255 — at that saturation, hue is dominated by
sensor/JPEG noise rather than real color, so the old thresholds
misclassified whole scenes (a real "forest" tile came back 0% vegetation,
98% built-up).

This version classifies each pixel by which channel actually *dominates*
it (excess-green for vegetation, excess-blue for water — both are
standard RGB-only vegetation/water indices used when no NIR/SWIR band is
available) rather than by absolute hue, which is far more robust to a
scene's overall color cast. It still can't perfectly separate bare soil
from built-up surfaces from RGB alone — that genuinely needs a NIR or
SWIR band — so built-up should be read as "not clearly vegetation or
water," not as a confident "this is urban" signal.
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

VEG_MARGIN = 5       # how far green must lead red to count as vegetation
WATER_MARGIN = 10    # how far blue must lead green to count as water
WATER_MAX_BRIGHTNESS = 100  # bright blue (e.g. a rooftop under haze) isn't water
BUILT_MAX_CHANNEL_RANGE = 22  # built-up/bare surfaces read as roughly neutral gray
BUILT_MIN_BRIGHTNESS = 75     # excludes shadow, which is also neutral gray but dark


def _channels(bgr: np.ndarray):
    b = bgr[:, :, 0].astype(np.float32)
    g = bgr[:, :, 1].astype(np.float32)
    r = bgr[:, :, 2].astype(np.float32)
    return b, g, r


def _water_mask(bgr: np.ndarray) -> np.ndarray:
    b, g, r = _channels(bgr)
    brightness = (r + g + b) / 3.0
    mask = (b > g) & (b > r) & (brightness < WATER_MAX_BRIGHTNESS) & ((b - g) > WATER_MARGIN)
    return (mask.astype(np.uint8)) * 255


def _vegetation_mask(bgr: np.ndarray) -> np.ndarray:
    b, g, r = _channels(bgr)
    mask = (g > r) & (g >= b) & ((g - r) > VEG_MARGIN)
    return (mask.astype(np.uint8)) * 255


def _built_up_mask(bgr: np.ndarray, water: np.ndarray, veg: np.ndarray) -> np.ndarray:
    b, g, r = _channels(bgr)
    brightness = (r + g + b) / 3.0
    chan_range = np.max(bgr, axis=2).astype(np.float32) - np.min(bgr, axis=2).astype(np.float32)
    candidate = (chan_range < BUILT_MAX_CHANNEL_RANGE) & (brightness > BUILT_MIN_BRIGHTNESS)
    candidate = (candidate.astype(np.uint8)) * 255
    exclude = cv2.bitwise_or(water, veg)
    return cv2.bitwise_and(candidate, cv2.bitwise_not(exclude))


def segment(image: Image.Image) -> Dict[str, Any]:
    bgr = pil_to_bgr(image)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    water = _water_mask(bgr)
    water = cv2.morphologyEx(water, cv2.MORPH_OPEN, kernel)

    veg = _vegetation_mask(bgr)
    veg = cv2.morphologyEx(veg, cv2.MORPH_OPEN, kernel)

    built = _built_up_mask(bgr, water, veg)
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
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    water = cv2.morphologyEx(_water_mask(bgr), cv2.MORPH_OPEN, kernel)
    veg = cv2.morphologyEx(_vegetation_mask(bgr), cv2.MORPH_OPEN, kernel)
    built = cv2.morphologyEx(_built_up_mask(bgr, water, veg), cv2.MORPH_OPEN, kernel)

    return {"water": water, "vegetation": veg, "built_up": built}
