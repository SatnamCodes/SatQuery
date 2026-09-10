#!/usr/bin/env python3
"""Pull small, real, public remote-sensing samples for SatQuery AI.

This replaces the synthetic test imagery used during initial development
with genuine satellite data and genuine human/automatically-verified
annotations, pulled from the datasets named in the SIH26167 brief:

  1. BigEarthNet (Sentinel-1 SAR + real per-patch land-cover labels, plus
     a best-effort match against BIFOLD-BigEarthNetv2-0/BigEarthNet.txt's
     real natural-language QA/captions)
  2. VRSBench    (real captions + QA + referring expressions)
  3. RSVQA       (real LR question/answer pairs over real Sentinel-2 chips)
  4. CDVQA       (real change-detection QA text; see README for the image
                  availability caveat)

IMPORTANT — read backend/data/README.md for exactly what each source
provides and, just as importantly, what it does NOT provide (BigEarthNet's
true Sentinel-1+Sentinel-2 co-registered pairs are ~50-60GB per modality on
HuggingFace and are not fetchable as a "small sample" — see README for the
documented substitution used instead).

Usage:
    source backend/venv/bin/activate
    pip install datasets huggingface_hub pillow numpy
    python backend/scripts/fetch_data.py
"""
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import requests
from PIL import Image

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

BEN_TARGET_PATCHES = 60
EUROSAT_PER_CLASS = 8
VRSBENCH_TARGET = 30
RSVQA_TARGET = 40
BEN_TXT_SCAN_LIMIT = 100000  # bounded scan when matching real QA to our patches


# --------------------------------------------------------------------------
# Small helper: read a handful of members out of a huge remote .zip without
# downloading the whole file, using HTTP range requests against the zip's
# central directory (both HF's CDN and Zenodo serve Accept-Ranges: bytes).
# --------------------------------------------------------------------------
class HTTPRangeFile(io.RawIOBase):
    def __init__(self, url, session=None):
        self.url = url
        self.session = session or requests.Session()
        head = self.session.head(url, allow_redirects=True, timeout=30)
        head.raise_for_status()
        self.length = int(head.headers["Content-Length"])
        self.pos = 0

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        elif whence == io.SEEK_END:
            self.pos = self.length + offset
        return self.pos

    def tell(self):
        return self.pos

    def readinto(self, b):
        n = len(b)
        if n == 0 or self.pos >= self.length:
            return 0
        end = min(self.pos + n, self.length) - 1
        r = self.session.get(
            self.url, headers={"Range": f"bytes={self.pos}-{end}"}, timeout=60
        )
        r.raise_for_status()
        data = r.content
        b[: len(data)] = data
        self.pos += len(data)
        return len(data)


def partial_zip_extract(url, wanted_names, dest_dir):
    """Extract only `wanted_names` members from a remote zip, without
    downloading it in full. Returns the set of names actually found."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    remote = HTTPRangeFile(url)
    found = set()
    with zipfile.ZipFile(remote) as zf:
        namelist = set(zf.namelist())
        for name in wanted_names:
            candidates = [name, f"images/{name}", name.split("/")[-1]]
            match = next((c for c in candidates if c in namelist), None)
            if match is None:
                # fall back to suffix match (some archives nest under a nested dir)
                match = next((n for n in namelist if n.endswith("/" + name) or n.endswith(name)), None)
            if match is None:
                continue
            data = zf.read(match)
            (dest_dir / Path(name).name).write_bytes(data)
            found.add(name)
    return found


# --------------------------------------------------------------------------
# 1. BigEarthNet — real Sentinel-1 SAR patches + real official labels
# --------------------------------------------------------------------------
def fetch_bigearthnet(out_dir: Path):
    from datasets import load_dataset
    from huggingface_hub import hf_hub_download

    print("[bigearthnet] streaming torchgeo/bigearthnet (real Sentinel-1 GRD patches)…")
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir = out_dir / "images"
    img_dir.mkdir(exist_ok=True)

    ds = load_dataset("torchgeo/bigearthnet", split="train", streaming=True)
    patches = {}  # patch_key -> {"VH": arr, "VV": arr}
    key_re = re.compile(r"^(S1[AB]_IW_GRDH_\S+)_(VH|VV)$")
    complete = {}
    max_rows_scanned = (BEN_TARGET_PATCHES + 20) * 2  # bands come in pairs, small safety margin

    for i, row in enumerate(ds):
        if i >= max_rows_scanned or len(complete) >= BEN_TARGET_PATCHES:
            break
        leaf = row["__key__"].rsplit("/", 1)[-1]
        m = key_re.match(leaf)
        if not m:
            continue
        patch_name, band = m.group(1), m.group(2)
        entry = patches.setdefault(patch_name, {})
        entry[band] = np.array(row["tif"], dtype=np.float32)
        if "VH" in entry and "VV" in entry:
            complete[patch_name] = entry

    print(f"[bigearthnet] got {len(complete)} real Sentinel-1 patches (VH+VV)")

    # Real official per-patch multi-label land-cover labels.
    print("[bigearthnet] downloading real metadata.parquet (official BigEarthNet labels)…")
    meta_path = hf_hub_download(
        "torchgeo/bigearthnet", "V2/metadata.parquet", repo_type="dataset"
    )
    import pandas as pd

    meta = pd.read_parquet(meta_path)
    # find the column that holds the S1 patch name to join on
    name_col = next(c for c in meta.columns if "s1" in c.lower() and "name" in c.lower())
    label_col = next(c for c in meta.columns if "label" in c.lower())
    meta_by_name = {row[name_col]: row[label_col] for _, row in meta.iterrows()}

    # Best-effort real natural-language QA match against BigEarthNet.txt,
    # bounded so the script finishes in reasonable time.
    print(f"[bigearthnet] scanning BigEarthNet.txt (up to {BEN_TXT_SCAN_LIMIT} rows) for matching real QA…")
    txt_qa_by_suffix = {}

    def tile_suffix(name):
        # last two underscore-separated ints identify the patch within its tile
        parts = name.split("_")
        return "_".join(parts[-2:]) if len(parts) >= 2 else name

    target_suffixes = {tile_suffix(n): n for n in complete}
    try:
        txt_ds = load_dataset(
            "BIFOLD-BigEarthNetv2-0/BigEarthNet.txt", split="all_data", streaming=True
        )
        for i, row in enumerate(txt_ds):
            if i >= BEN_TXT_SCAN_LIMIT:
                break
            suf = tile_suffix(row["s1_name"])
            if suf in target_suffixes and target_suffixes[suf] not in txt_qa_by_suffix:
                txt_qa_by_suffix[target_suffixes[suf]] = {
                    "question": row["input"],
                    "answer": row["output"],
                    "type": row["type"],
                    "category": row["category"],
                    "country": row["country"],
                    "season": row["season"],
                }
    except Exception as e:
        print(f"[bigearthnet] BigEarthNet.txt scan failed non-fatally: {e}")

    print(f"[bigearthnet] real BigEarthNet.txt QA matched for {len(txt_qa_by_suffix)}/{len(complete)} patches")

    manifest = []
    for patch_name, bands in complete.items():
        vv = _sar_db_to_uint8(bands["VV"])
        vh = _sar_db_to_uint8(bands["VH"])
        rgb = np.dstack([vv, vh, ((vv.astype(int) + vh.astype(int)) // 2).astype(np.uint8)])
        fname = f"{patch_name}.png"
        Image.fromarray(rgb, mode="RGB").save(img_dir / fname)

        labels = meta_by_name.get(patch_name)
        labels_list = list(labels) if labels is not None else []
        caption = (
            f"Sentinel-1 SAR patch. Official BigEarthNet land-cover labels: {', '.join(labels_list)}."
            if labels_list
            else "Sentinel-1 SAR patch (no official label match found)."
        )
        entry = {
            "file": fname,
            "modality": "sar",
            "source": "torchgeo/bigearthnet (real Sentinel-1 GRD, bands VV/VH)",
            "patch_name": patch_name,
            "official_labels": labels_list,
            "caption": caption,
        }
        if patch_name in txt_qa_by_suffix:
            entry["real_qa"] = txt_qa_by_suffix[patch_name]
            entry["caption"] = txt_qa_by_suffix[patch_name]["question"] + " -> " + txt_qa_by_suffix[patch_name]["answer"]
        manifest.append(entry)

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[bigearthnet] wrote {len(manifest)} real samples to {out_dir}")
    return manifest


def _sar_db_to_uint8(arr):
    arr = np.nan_to_num(arr, nan=0.0, neginf=0.0)
    lo, hi = np.percentile(arr, 2), np.percentile(arr, 98)
    if hi <= lo:
        hi = lo + 1e-6
    scaled = np.clip((arr - lo) / (hi - lo), 0, 1)
    return (scaled * 255).astype(np.uint8)


# --------------------------------------------------------------------------
# 2. EuroSAT — real Sentinel-2 optical chips, used as the optical-modality
#    sample source (see data/README.md for why true BigEarthNet S2 pixels
#    were not fetchable in this environment)
# --------------------------------------------------------------------------
def fetch_eurosat(out_dir: Path):
    from datasets import load_dataset

    print("[eurosat] streaming tanganke/eurosat (real Sentinel-2 RGB chips)…")
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir = out_dir / "images"
    img_dir.mkdir(exist_ok=True)

    ds = load_dataset("tanganke/eurosat", split="train", streaming=True)
    class_names = ds.features["label"].names
    per_class_count = {}
    manifest = []

    for i, row in enumerate(ds):
        label_name = class_names[row["label"]]
        if per_class_count.get(label_name, 0) >= EUROSAT_PER_CLASS:
            continue
        per_class_count[label_name] = per_class_count.get(label_name, 0) + 1
        fname = f"eurosat_{label_name.replace(' ', '_')}_{per_class_count[label_name]:02d}.png"
        row["image"].convert("RGB").save(img_dir / fname)
        manifest.append({
            "file": fname,
            "modality": "optical",
            "source": "tanganke/eurosat (real Sentinel-2 derived RGB, EuroSAT benchmark)",
            "label": label_name,
            "caption": f"Sentinel-2 optical chip. Official EuroSAT land-use label: {label_name}.",
        })
        if sum(per_class_count.values()) >= EUROSAT_PER_CLASS * len(class_names):
            break

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[eurosat] wrote {len(manifest)} real samples to {out_dir}")
    return manifest


# --------------------------------------------------------------------------
# 3. VRSBench — real captions + VQA + referring expressions
# --------------------------------------------------------------------------
def fetch_vrsbench(out_dir: Path):
    from huggingface_hub import hf_hub_download

    print("[vrsbench] downloading real VRSBench eval annotation files…")
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir = out_dir / "images"

    cap_path = hf_hub_download("xiang709/VRSBench", "VRSBench_EVAL_Cap.json", repo_type="dataset")
    vqa_path = hf_hub_download("xiang709/VRSBench", "VRSBench_EVAL_vqa.json", repo_type="dataset")

    captions = json.loads(Path(cap_path).read_text())
    vqas = json.loads(Path(vqa_path).read_text())

    caption_by_image = {}
    for c in captions:
        caption_by_image.setdefault(c["image_id"], c.get("ground_truth") or c.get("caption"))

    qa_by_image = {}
    for q in vqas:
        qa_by_image.setdefault(q["image_id"], []).append({
            "question": q["question"],
            "answer": q["ground_truth"],
            "type": q.get("type"),
        })

    target_images = list(dict.fromkeys(list(caption_by_image) + list(qa_by_image)))[:VRSBENCH_TARGET]

    print(f"[vrsbench] extracting {len(target_images)} real images from Images_val.zip via HTTP range requests…")
    from huggingface_hub import hf_hub_url

    zip_url = hf_hub_url("xiang709/VRSBench", "Images_val.zip", repo_type="dataset")
    found = partial_zip_extract(zip_url, target_images, img_dir)
    print(f"[vrsbench] extracted {len(found)}/{len(target_images)} real images")

    manifest = []
    for name in target_images:
        if name not in found:
            continue
        manifest.append({
            "file": name,
            "modality": "optical",
            "source": "xiang709/VRSBench (real human-verified caption + VQA, val split)",
            "caption": caption_by_image.get(name),
            "qa_pairs": qa_by_image.get(name, []),
        })

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[vrsbench] wrote {len(manifest)} real samples to {out_dir}")
    return manifest


# --------------------------------------------------------------------------
# 4. RSVQA (LR) — real Sentinel-2-derived chips + real QA pairs
# --------------------------------------------------------------------------
def fetch_rsvqa(out_dir: Path):
    print("[rsvqa] downloading real RSVQA-LR train question/answer/image JSON…")
    out_dir.mkdir(parents=True, exist_ok=True)
    img_dir = out_dir / "images"
    img_dir.mkdir(exist_ok=True)

    base = "https://zenodo.org/api/records/6344334/files"
    images_meta = requests.get(f"{base}/LR_split_train_images.json/content", timeout=60).json()["images"]
    questions = requests.get(f"{base}/LR_split_train_questions.json/content", timeout=60).json()["questions"]
    answers = requests.get(f"{base}/LR_split_train_answers.json/content", timeout=60).json()["answers"]

    answer_by_id = {a["id"]: a["answer"] for a in answers if "answer" in a}
    questions_by_img = {}
    for q in questions:
        if not q.get("answers_ids") or "question" not in q:
            continue
        ans = answer_by_id.get(q["answers_ids"][0])
        if ans is None:
            continue
        questions_by_img.setdefault(q["img_id"], []).append(
            {"question": q["question"], "answer": ans, "type": q["type"]}
            )

    target_ids = [im["id"] for im in images_meta if im["id"] in questions_by_img][:RSVQA_TARGET]

    print(f"[rsvqa] downloading Images_LR.zip (~95MB, official LR sample) to extract {len(target_ids)} real images…")
    zip_bytes = requests.get(f"{base}/Images_LR.zip/content", timeout=180).content
    extracted = 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = zf.namelist()
        for img_id in target_ids:
            match = next((n for n in namelist if Path(n).stem == str(img_id)), None)
            if not match:
                continue
            data = zf.read(match)
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.save(img_dir / f"{img_id}.png")
            extracted += 1
    del zip_bytes
    print(f"[rsvqa] extracted {extracted}/{len(target_ids)} real images")

    manifest = []
    for img_id in target_ids:
        if not (img_dir / f"{img_id}.png").exists():
            continue
        img_meta = next(im for im in images_meta if im["id"] == img_id)
        manifest.append({
            "file": f"{img_id}.png",
            "modality": "optical",
            "source": "RSVQA-LR (real Sentinel-2 10m RGB chips, Zenodo record 6344334, train split)",
            "original_sentinel2_name": img_meta.get("original_name"),
            "qa_pairs": questions_by_img.get(img_id, []),
            "caption": questions_by_img.get(img_id, [{}])[0].get("question", ""),
        })

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[rsvqa] wrote {len(manifest)} real samples to {out_dir}")
    return manifest


# --------------------------------------------------------------------------
# 5. CDVQA — real change-detection QA text (no public image download link;
#    see data/README.md)
# --------------------------------------------------------------------------
def fetch_cdvqa(out_dir: Path):
    print("[cdvqa] downloading real CDVQA validation QA JSON (images not publicly downloadable, see README)…")
    out_dir.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/YZHJessica/CDVQA/main"

    questions = requests.get(f"{base}/Val_questions.json", timeout=60).json()
    answers = requests.get(f"{base}/Val_answers.json", timeout=60).json()
    images = requests.get(f"{base}/Val_images.json", timeout=60).json()

    sample_n = 40
    manifest = {
        "note": (
            "CDVQA ships only question/answer/image-reference JSON on its official "
            "GitHub repo (github.com/YZHJessica/CDVQA); the underlying bi-temporal "
            "image pairs come from the SECOND change-detection dataset and are not "
            "behind a public direct-download link (author-mediated access only). "
            "We therefore keep the real QA text for documentation and for wiring the "
            "'benchmark reference answer' comparison feature's schema, but the sample "
            "gallery cannot show real CDVQA thumbnails — see backend/data/README.md."
        ),
        "questions": questions[:sample_n] if isinstance(questions, list) else questions,
        "answers": answers[:sample_n] if isinstance(answers, list) else answers,
        "images": images[:sample_n] if isinstance(images, list) else images,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[cdvqa] wrote real QA-only manifest to {out_dir} (no images available)")
    return manifest


STEPS = {
    "bigearthnet": lambda: fetch_bigearthnet(DATA_ROOT / "bigearthnet_sample"),
    "eurosat": lambda: fetch_eurosat(DATA_ROOT / "bigearthnet_sample_optical"),
    "vrsbench": lambda: fetch_vrsbench(DATA_ROOT / "vrsbench_sample"),
    "rsvqa": lambda: fetch_rsvqa(DATA_ROOT / "rsvqa_sample"),
    "cdvqa": lambda: fetch_cdvqa(DATA_ROOT / "cdvqa_sample"),
}


def main():
    import sys

    requested = sys.argv[1:] or list(STEPS)
    print("=" * 70)
    print("SatQuery AI — fetching real remote-sensing sample data")
    print("=" * 70)

    for name in requested:
        STEPS[name]()

    print("=" * 70)
    print("Done. See backend/data/README.md for full provenance notes.")
    print("=" * 70)


if __name__ == "__main__":
    main()
