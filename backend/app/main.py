"""SatQuery AI backend — FastAPI app.

Endpoints:
  POST /api/session  create a session from 1-2 uploaded images
  POST /api/query     ask a question against a session's images
  GET  /api/health    liveness + VLM/tool-registry status
"""
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from pydantic import BaseModel

from .services import samples as samples_service
from .services.gemini_vlm import vlm
from .services.imgutils import load_image_bytes
from .services.orchestrator import TOOL_REGISTRY, route

app = FastAPI(title="SatQuery AI Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
if DATA_DIR.exists():
    app.mount("/api/samples/media", StaticFiles(directory=DATA_DIR), name="sample-media")

SESSION_TTL_SECONDS = 60 * 60  # 1 hour
VALID_MODALITIES = {"optical", "sar"}
VALID_PAIR_TYPES = {"bi_temporal", "cross_modal"}

SESSIONS: Dict[str, dict] = {}


def _purge_expired() -> None:
    now = time.time()
    expired = [sid for sid, s in SESSIONS.items() if now - s["created_at"] > SESSION_TTL_SECONDS]
    for sid in expired:
        del SESSIONS[sid]


def _get_session(session_id: str) -> dict:
    _purge_expired()
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or expired")
    return session


class QueryRequest(BaseModel):
    session_id: str
    question: str


class SampleSessionRequest(BaseModel):
    sample_id: str


def _validate_pair(modality_1: str, modality_2: Optional[str], pair_type: Optional[str]) -> None:
    if modality_1 not in VALID_MODALITIES:
        raise HTTPException(status_code=400, detail=f"modality_1 must be one of {sorted(VALID_MODALITIES)}")
    if modality_2 is None:
        return
    if modality_2 not in VALID_MODALITIES:
        raise HTTPException(status_code=400, detail=f"modality_2 must be one of {sorted(VALID_MODALITIES)}")
    if pair_type is None:
        raise HTTPException(status_code=400, detail="pair_type is required when two images are provided")
    if pair_type not in VALID_PAIR_TYPES:
        raise HTTPException(status_code=400, detail=f"pair_type must be one of {sorted(VALID_PAIR_TYPES)}")
    if pair_type == "bi_temporal" and modality_1 != modality_2:
        raise HTTPException(
            status_code=400,
            detail="bi_temporal pairs must share the same modality (both optical or both sar)",
        )
    if pair_type == "cross_modal" and {modality_1, modality_2} != VALID_MODALITIES:
        raise HTTPException(
            status_code=400,
            detail="cross_modal pairs require exactly one optical and one sar image",
        )


def _create_session(images: List[Image.Image], modalities: List[str], pair_type: Optional[str]) -> dict:
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {
        "created_at": time.time(),
        "images": images,
        "modalities": modalities,
        "pair_type": pair_type,
    }
    return {
        "session_id": session_id,
        "modalities": modalities,
        "pair_type": pair_type,
        "image_count": len(images),
        "ttl_seconds": SESSION_TTL_SECONDS,
    }


@app.post("/api/session")
async def create_session(
    image_1: UploadFile = File(...),
    modality_1: str = Form(...),
    image_2: Optional[UploadFile] = File(None),
    modality_2: Optional[str] = Form(None),
    pair_type: Optional[str] = Form(None),
):
    modality_1 = modality_1.lower()
    modality_2 = modality_2.lower() if modality_2 else None
    pair_type = pair_type.lower() if pair_type else None

    try:
        img1 = load_image_bytes(await image_1.read())
        img1.load()
    except Exception:
        raise HTTPException(status_code=400, detail="image_1 is not a valid image file")

    images = [img1]
    modalities = [modality_1]

    if image_2 is not None:
        try:
            img2 = load_image_bytes(await image_2.read())
            img2.load()
        except Exception:
            raise HTTPException(status_code=400, detail="image_2 is not a valid image file")
        _validate_pair(modality_1, modality_2, pair_type)
        images.append(img2)
        modalities.append(modality_2)
    elif pair_type is not None:
        raise HTTPException(status_code=400, detail="pair_type was provided but image_2 is missing")
    else:
        _validate_pair(modality_1, None, None)

    return _create_session(images, modalities, pair_type)


@app.get("/api/samples")
async def list_samples():
    return samples_service.get_catalog()


@app.post("/api/session/sample")
async def create_session_from_sample(req: SampleSessionRequest):
    sample = samples_service.get_sample(req.sample_id)
    if sample is None:
        raise HTTPException(status_code=404, detail=f"Unknown sample_id: {req.sample_id}")

    spec = sample["session_spec"]
    folder, filename = spec["image_1"]
    path = samples_service.resolve_image_path(folder, filename)
    if not path.exists():
        raise HTTPException(status_code=500, detail=f"Sample image missing on disk: {path}")
    img1 = Image.open(path)
    img1.load()
    images = [img1]
    modalities = [spec["modality_1"]]

    if "image_2" in spec:
        folder2, filename2 = spec["image_2"]
        path2 = samples_service.resolve_image_path(folder2, filename2)
        if not path2.exists():
            raise HTTPException(status_code=500, detail=f"Sample image missing on disk: {path2}")
        img2 = Image.open(path2)
        img2.load()
        images.append(img2)
        modalities.append(spec["modality_2"])

    session = _create_session(images, modalities, spec.get("pair_type"))
    SESSIONS[session["session_id"]]["benchmark_reference"] = sample.get("benchmark_reference")
    session["sample_id"] = req.sample_id
    session["sample_caption"] = sample.get("caption")
    return session


@app.post("/api/query")
async def query(req: QueryRequest):
    session = _get_session(req.session_id)
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")

    result = route(
        question=req.question,
        images=session["images"],
        modalities=session["modalities"],
        pair_type=session["pair_type"],
    )

    benchmark_reference = session.get("benchmark_reference")
    if benchmark_reference and result.get("task") == "change_detection":
        # Real ground-truth answer from the CDVQA benchmark, shown next to
        # SatQuery's own answer so the comparison is visible live rather
        # than asserted. Populated only for CDVQA-sourced samples — see
        # backend/data/README.md for why the shipped catalog currently has
        # none with paired imagery.
        result["benchmark_reference"] = benchmark_reference

    return result


@app.get("/api/health")
async def health():
    _purge_expired()
    return {
        "status": "ok",
        "vlm_configured": vlm.configured,
        "registry": {name: spec for name, spec in TOOL_REGISTRY.items()},
        "active_sessions": len(SESSIONS),
    }
