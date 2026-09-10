"""Bi-temporal change detection between two optical images of the same scene.

Pipeline: grayscale absolute difference -> Gaussian blur (denoise) ->
Otsu automatic thresholding -> morphological open/close cleanup ->
contour extraction -> stats + an amber-boxed / red-heat overlay.
"""
from typing import Any, Dict

import cv2
import numpy as np
from PIL import Image

from .imgutils import bgr_to_base64_png, pil_to_bgr

MIN_CONTOUR_AREA = 25  # px^2, filters out single-pixel noise blobs


def detect_change(image_before: Image.Image, image_after: Image.Image) -> Dict[str, Any]:
    before_bgr = pil_to_bgr(image_before)
    after_bgr = pil_to_bgr(image_after)

    h, w = before_bgr.shape[:2]
    if after_bgr.shape[:2] != (h, w):
        after_bgr = cv2.resize(after_bgr, (w, h), interpolation=cv2.INTER_AREA)

    gray_before = cv2.cvtColor(before_bgr, cv2.COLOR_BGR2GRAY)
    gray_after = cv2.cvtColor(after_bgr, cv2.COLOR_BGR2GRAY)

    diff = cv2.absdiff(gray_before, gray_after)
    blurred = cv2.GaussianBlur(diff, (5, 5), 0)

    threshold_value, mask = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= MIN_CONTOUR_AREA]

    bboxes = []
    for c in contours:
        x, y, cw, ch = cv2.boundingRect(c)
        bboxes.append({
            "x": int(x), "y": int(y), "width": int(cw), "height": int(ch),
            "area_px": int(cv2.contourArea(c)),
        })
    bboxes.sort(key=lambda b: b["area_px"], reverse=True)

    changed_px = int(np.count_nonzero(mask))
    total_px = int(mask.shape[0] * mask.shape[1])
    change_percent = round(100.0 * changed_px / total_px, 3) if total_px else 0.0

    overlay = _build_overlay(after_bgr, mask, bboxes)

    return {
        "change_percent": change_percent,
        "region_count": len(bboxes),
        "bboxes": bboxes,
        "otsu_threshold": float(threshold_value),
        "overlay_png_base64": bgr_to_base64_png(overlay),
        "image_size": {"width": w, "height": h},
    }


def _build_overlay(base_bgr: np.ndarray, mask: np.ndarray, bboxes) -> np.ndarray:
    overlay = base_bgr.copy()

    # Red heat wash over the changed-pixel mask.
    heat = np.zeros_like(overlay)
    heat[:, :] = (0, 0, 255)  # BGR red
    heat_mask = mask.astype(bool)
    overlay[heat_mask] = cv2.addWeighted(
        overlay, 0.55, heat, 0.45, 0
    )[heat_mask]

    # Amber bounding boxes for each detected region.
    amber = (0, 191, 255)  # BGR amber
    for b in bboxes:
        x, y, cw, ch = b["x"], b["y"], b["width"], b["height"]
        cv2.rectangle(overlay, (x, y), (x + cw, y + ch), amber, 2)

    return overlay
