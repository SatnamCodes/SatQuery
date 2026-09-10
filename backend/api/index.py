"""Vercel Python entrypoint: exposes the FastAPI ASGI app so Vercel's
Python runtime can serve it as a serverless function. Nothing to see here
beyond the import — all real logic lives in app/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402
