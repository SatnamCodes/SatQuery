"""Shared image I/O helpers used across the vision services."""
import base64
from io import BytesIO

import cv2
import numpy as np
from PIL import Image


def pil_to_bgr(img: Image.Image) -> np.ndarray:
    """Convert a PIL image (any mode) to an OpenCV-style BGR ndarray."""
    rgb = img.convert("RGB")
    arr = np.array(rgb)
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def bgr_to_base64_png(bgr: np.ndarray) -> str:
    """Encode a BGR ndarray as a base64 PNG string (no data-URI prefix)."""
    ok, buf = cv2.imencode(".png", bgr)
    if not ok:
        raise ValueError("Failed to encode image as PNG")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def bgr_to_data_uri(bgr: np.ndarray) -> str:
    return f"data:image/png;base64,{bgr_to_base64_png(bgr)}"


def load_image_bytes(data: bytes) -> Image.Image:
    return Image.open(BytesIO(data))
