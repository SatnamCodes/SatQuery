"""Optical + SAR fusion.

SAR backscatter physics used here:
  - Calm water is a near-specular reflector -> almost all energy bounces
    away from the sensor -> water reads as DARK / low backscatter.
  - Buildings and other hard urban surfaces produce strong double-bounce
    reflection off ground-wall corners -> built-up reads as BRIGHT / high
    backscatter.

We derive water/built-up candidate masks from the SAR image using simple
intensity thresholds and cross-check them against the optical HSV masks
from segmentation.py. Agreement between both modalities is the strongest
signal a field officer can trust ("high confidence"); a flag from only one
modality is still worth a look but should be treated as tentative
("possible").
"""
from typing import Any, Dict

import cv2
import numpy as np
from PIL import Image

from .imgutils import bgr_to_base64_png, pil_to_bgr
from .segmentation import get_masks as optical_masks

SAR_WATER_PERCENTILE = 25   # darkest ~25% of SAR intensity -> candidate water
SAR_BUILTUP_PERCENTILE = 80  # brightest ~20% of SAR intensity -> candidate built-up

HIGH_CONF_COLOR = {
    "water": (255, 80, 0),
    "built_up": (0, 0, 255),
}
POSSIBLE_COLOR = {
    "water": (255, 200, 150),
    "built_up": (140, 140, 255),
}


def _sar_gray(image: Image.Image, shape_hw) -> np.ndarray:
    bgr = pil_to_bgr(image)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = shape_hw
    if gray.shape[:2] != (h, w):
        gray = cv2.resize(gray, (w, h), interpolation=cv2.INTER_AREA)
    return gray


def fuse(optical_image: Image.Image, sar_image: Image.Image) -> Dict[str, Any]:
    opt_bgr = pil_to_bgr(optical_image)
    h, w = opt_bgr.shape[:2]
    sar_gray = _sar_gray(sar_image, (h, w))

    water_thresh = float(np.percentile(sar_gray, SAR_WATER_PERCENTILE))
    built_thresh = float(np.percentile(sar_gray, SAR_BUILTUP_PERCENTILE))

    # Strict inequalities: a percentile can land exactly on a flat background
    # value (e.g. a uniform SAR backdrop), and <=/>= would then flag that
    # entire background as a candidate region.
    sar_water = (sar_gray < water_thresh).astype(np.uint8) * 255
    sar_built = (sar_gray > built_thresh).astype(np.uint8) * 255

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    sar_water = cv2.morphologyEx(sar_water, cv2.MORPH_OPEN, kernel)
    sar_built = cv2.morphologyEx(sar_built, cv2.MORPH_OPEN, kernel)

    opt = optical_masks(optical_image)
    opt_water, opt_built = opt["water"], opt["built_up"]
    if opt_water.shape != (h, w):
        opt_water = cv2.resize(opt_water, (w, h), interpolation=cv2.INTER_NEAREST)
        opt_built = cv2.resize(opt_built, (w, h), interpolation=cv2.INTER_NEAREST)

    tiers = {}
    for label, opt_mask, sar_mask in (
        ("water", opt_water, sar_water),
        ("built_up", opt_built, sar_built),
    ):
        both = cv2.bitwise_and(opt_mask, sar_mask)
        either = cv2.bitwise_or(opt_mask, sar_mask)
        possible_only = cv2.bitwise_and(either, cv2.bitwise_not(both))
        tiers[label] = {"high_confidence": both, "possible": possible_only}

    total_px = h * w
    stats = {}
    for label, tier_masks in tiers.items():
        stats[label] = {
            "high_confidence_percent": round(
                100.0 * np.count_nonzero(tier_masks["high_confidence"]) / total_px, 3
            ),
            "possible_percent": round(
                100.0 * np.count_nonzero(tier_masks["possible"]) / total_px, 3
            ),
        }

    overlay = opt_bgr.copy()
    for label, tier_masks in tiers.items():
        possible_layer = np.zeros_like(overlay)
        possible_layer[:, :] = POSSIBLE_COLOR[label]
        m = tier_masks["possible"].astype(bool)
        overlay[m] = cv2.addWeighted(overlay, 0.6, possible_layer, 0.4, 0)[m]

        high_layer = np.zeros_like(overlay)
        high_layer[:, :] = HIGH_CONF_COLOR[label]
        m = tier_masks["high_confidence"].astype(bool)
        overlay[m] = cv2.addWeighted(overlay, 0.45, high_layer, 0.55, 0)[m]

    return {
        "stats": stats,
        "sar_thresholds": {"water_max_intensity": water_thresh, "built_up_min_intensity": built_thresh},
        "overlay_png_base64": bgr_to_base64_png(overlay),
        "image_size": {"width": w, "height": h},
        "legend": {
            "high_confidence": "Both optical and SAR agree",
            "possible": "Only one modality flags this area",
        },
    }
