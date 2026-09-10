"""Builds the /api/samples catalog from the real datasets pulled by
scripts/fetch_data.py (see backend/data/README.md for provenance).

Nothing here is synthesized: every entry's image file and caption/QA text
comes straight from a manifest.json written by fetch_data.py.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_ROOT = Path(__file__).resolve().parent.parent.parent / "data"

SINGLE_PER_SOURCE = 6
PAIR_COUNT = 4


def _load_manifest(folder: str) -> Optional[List[Dict[str, Any]]]:
    path = DATA_ROOT / folder / "manifest.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    return data if isinstance(data, list) else None


def _media_url(folder: str, filename: str) -> str:
    return f"/api/samples/media/{folder}/images/{filename}"


def build_catalog() -> Dict[str, Any]:
    vrsbench = _load_manifest("vrsbench_sample") or []
    rsvqa = _load_manifest("rsvqa_sample") or []
    eurosat = _load_manifest("bigearthnet_sample_optical") or []
    bigearthnet = _load_manifest("bigearthnet_sample") or []
    cdvqa_path = DATA_ROOT / "cdvqa_sample" / "manifest.json"
    cdvqa = json.loads(cdvqa_path.read_text()) if cdvqa_path.exists() else None

    single = []
    for entry in vrsbench[:SINGLE_PER_SOURCE]:
        single.append({
            "id": f"vrsbench:{entry['file']}",
            "pair_type": None,
            "modality": "optical",
            "caption": entry.get("caption"),
            "source": entry["source"],
            "thumbnail_url": _media_url("vrsbench_sample", entry["file"]),
            "session_spec": {"image_1": ("vrsbench_sample", entry["file"]), "modality_1": "optical"},
        })
    for entry in rsvqa[:SINGLE_PER_SOURCE]:
        qa = entry.get("qa_pairs") or []
        caption = f"{qa[0]['question']} -> {qa[0]['answer']}" if qa else entry.get("caption")
        single.append({
            "id": f"rsvqa:{entry['file']}",
            "pair_type": None,
            "modality": "optical",
            "caption": caption,
            "source": entry["source"],
            "thumbnail_url": _media_url("rsvqa_sample", entry["file"]),
            "session_spec": {"image_1": ("rsvqa_sample", entry["file"]), "modality_1": "optical"},
        })
    for entry in eurosat[:SINGLE_PER_SOURCE]:
        single.append({
            "id": f"eurosat:{entry['file']}",
            "pair_type": None,
            "modality": "optical",
            "caption": entry.get("caption"),
            "source": entry["source"],
            "thumbnail_url": _media_url("bigearthnet_sample_optical", entry["file"]),
            "session_spec": {"image_1": ("bigearthnet_sample_optical", entry["file"]), "modality_1": "optical"},
        })

    bi_temporal = []
    for i in range(0, min(len(bigearthnet) - 1, PAIR_COUNT * 2), 2):
        a, b = bigearthnet[i], bigearthnet[i + 1]
        bi_temporal.append({
            "id": f"bigearthnet-bitemporal:{a['file']}+{b['file']}",
            "pair_type": "bi_temporal",
            "modality": "sar",
            "caption": f"Two real Sentinel-1 BigEarthNet patches ({a['patch_name']}, {b['patch_name']}) — different locations, not a true time series of one site; see data/README.md.",
            "source": a["source"],
            "thumbnail_url": _media_url("bigearthnet_sample", a["file"]),
            "thumbnail_url_2": _media_url("bigearthnet_sample", b["file"]),
            "session_spec": {
                "image_1": ("bigearthnet_sample", a["file"]),
                "modality_1": "sar",
                "image_2": ("bigearthnet_sample", b["file"]),
                "modality_2": "sar",
                "pair_type": "bi_temporal",
            },
        })

    cross_modal = []
    for i, sar_entry in enumerate(bigearthnet[:PAIR_COUNT]):
        if i >= len(eurosat):
            break
        opt_entry = eurosat[i]
        cross_modal.append({
            "id": f"bigearthnet-crossmodal:{sar_entry['file']}+{opt_entry['file']}",
            "pair_type": "cross_modal",
            "modality": "mixed",
            "caption": f"Real Sentinel-1 SAR ({sar_entry['patch_name']}) paired with a real Sentinel-2 optical chip ({opt_entry['label']}) — not geographically co-registered; see data/README.md.",
            "source": f"{sar_entry['source']} + {opt_entry['source']}",
            "thumbnail_url": _media_url("bigearthnet_sample_optical", opt_entry["file"]),
            "thumbnail_url_2": _media_url("bigearthnet_sample", sar_entry["file"]),
            "session_spec": {
                "image_1": ("bigearthnet_sample_optical", opt_entry["file"]),
                "modality_1": "optical",
                "image_2": ("bigearthnet_sample", sar_entry["file"]),
                "modality_2": "sar",
                "pair_type": "cross_modal",
            },
        })

    return {
        "single": single,
        "bi_temporal": bi_temporal,
        "cross_modal": cross_modal,
        "cdvqa_note": (cdvqa or {}).get("note"),
    }


_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_INDEX_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def get_catalog() -> Dict[str, Any]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is None:
        _CATALOG_CACHE = build_catalog()
    return _CATALOG_CACHE


def get_sample(sample_id: str) -> Optional[Dict[str, Any]]:
    global _INDEX_CACHE
    if _INDEX_CACHE is None:
        catalog = get_catalog()
        _INDEX_CACHE = {}
        for group in ("single", "bi_temporal", "cross_modal"):
            for entry in catalog[group]:
                _INDEX_CACHE[entry["id"]] = entry
    return _INDEX_CACHE.get(sample_id)


def resolve_image_path(folder: str, filename: str) -> Path:
    return DATA_ROOT / folder / "images" / filename
