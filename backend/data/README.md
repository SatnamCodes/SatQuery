# SatQuery AI — sample data provenance

Everything under `backend/data/` was pulled by `backend/scripts/fetch_data.py`
from public, real remote-sensing sources. Nothing here is synthetic. Run
`python backend/scripts/fetch_data.py` (from an activated `backend/venv`
with `datasets`, `huggingface_hub`, `pandas`, `pyarrow`, `pillow`, `numpy`
installed) to re-pull everything, or `python backend/scripts/fetch_data.py
<step>` (`bigearthnet`, `eurosat`, `vrsbench`, `rsvqa`, `cdvqa`) to re-run
one source.

## 1. `bigearthnet_sample/` — real Sentinel-1 SAR + real BigEarthNet labels/QA

**What's actually here:** 60 real Sentinel-1 GRD patches (VV+VH bands),
streamed from
[`torchgeo/bigearthnet`](https://huggingface.co/datasets/torchgeo/bigearthnet)
and rendered to PNG (VV → red channel, VH → green channel, mean → blue,
each percentile-stretched — a viewable false-color rendering of the two
real backscatter bands, not an invented image). Each patch is joined
against two more real sources:

- `V2/metadata.parquet` from the same `torchgeo/bigearthnet` repo — the
  **official BigEarthNet multi-label land-cover annotation** for that exact
  patch (e.g. "Arable land", "Broad-leaved forest", "Inland waters").
- [`BIFOLD-BigEarthNetv2-0/BigEarthNet.txt`](https://huggingface.co/datasets/BIFOLD-BigEarthNetv2-0/BigEarthNet.txt) — the
  dataset the SIH26167 brief names by ID. It is a **real, human/automatically-verified
  VQA+captioning benchmark over BigEarthNet** (9.55M rows: `input` question,
  `output` answer, `type`, `category`, plus lat/lon/country/season). We
  stream-matched its `s1_name` field against the 60 patches we hold (by
  tile+patch-grid suffix, e.g. `33UUP_61_39`) and got a **60/60 real match
  rate** — every sample's `caption` field is a genuine BigEarthNet.txt
  question→answer pair, not a template.

**Why not the true Sentinel-1+Sentinel-2 co-registered pairs the brief
implies:** BigEarthNet.txt ships *only text*; the imagery must be fetched
separately from the full BigEarthNet v2.0 archive, which on HuggingFace is
packaged as two ~50-60GB split tar files per modality
(`BigEarthNet-S1.tar.gzaa/ab`, `BigEarthNet-S2.tar.gzaa/ab`, confirmed via
`huggingface_hub.HfApi.repo_info`). `datasets` streaming reads these tars
sequentially — we confirmed empirically that the S2 shard doesn't begin
until *after* the entire ~54GB S1 shard has been read, which made a "small
sample" of real S2 pixels infeasible in this environment. We could and did
get real S1 quickly (streaming reads only as many bytes as needed from the
*start* of its shard). Real S2 optical imagery is instead sourced from
EuroSAT — see below — and kept in a separate folder so provenance stays
honest and un-conflated.

**License:** CDLA Permissive 1.0 (BigEarthNet.txt), BigEarthNet v2.0's own
license for the underlying imagery/labels (research use, see bigearth.net).

## 2. `bigearthnet_sample_optical/` — real Sentinel-2 optical chips (EuroSAT)

**What's here:** 80 real Sentinel-2-derived RGB chips (8 per class × 10
classes), streamed from
[`tanganke/eurosat`](https://huggingface.co/datasets/tanganke/eurosat),
with EuroSAT's own official land-use class label as the real annotation
(e.g. "forest", "river", "residential buildings or homes or apartments").

**Why this folder exists / naming note:** this is the practical substitute
for real BigEarthNet-native S2 imagery described above — genuinely real
Sentinel-2 satellite data, just not from the BigEarthNet archive itself.
Used as the app's "optical" sample source (single-image and one side of
cross-modal demos).

**License:** EuroSAT is released for research use (MIT-style redistribution
per the `tanganke/eurosat` HF card); original Sentinel-2 data is
Copernicus/ESA open data.

## 3. `vrsbench_sample/` — real captions, VQA, referring expressions

**What's here:** 30 real images (of the VRSBench validation split) with
their real human-verified caption and real question/answer pairs, pulled
from
[`xiang709/VRSBench`](https://huggingface.co/datasets/xiang709/VRSBench)'s
official `VRSBench_EVAL_Cap.json` / `VRSBench_EVAL_vqa.json` annotation
files. The images themselves live in a ~4GB `Images_val.zip` on that
repo — rather than downloading the whole archive, we open it with HTTP
range requests (`HTTPRangeFile` in `fetch_data.py`) and read only the
central directory + the ~30 specific member files we need, so the "small
sample, not the full benchmark" instruction is met literally at the byte
level, not just by count.

**License:** VRSBench is released for research/non-commercial use — see
the [VRSBench GitHub repo](https://github.com/lx709/VRSBench) and
NeurIPS 2024 Datasets & Benchmarks paper for full terms.

## 4. `rsvqa_sample/` — real RSVQA-LR question/answer pairs over real Sentinel-2 chips

**What's here:** 40 real 256×256 Sentinel-2 RGB chips (10m resolution) with
their real question/answer pairs, from the RSVQA Low Resolution dataset
(Zenodo record
[6344334](https://zenodo.org/record/6344334), the dataset's own official
distribution — `rsvqa.sylvainlobry.com` points here). Each manifest entry
also carries `original_sentinel2_name`, the real Sentinel-2 product ID the
chip was cut from (e.g. `S2B_MSIL1C_20181010T104019_...`). We used the
`train` split's JSON files because the `test` split ships with answers
withheld for leaderboard integrity (`active: false`, no `answer` field) —
confirmed by inspecting both before choosing.

**License:** CC BY 4.0 (per the Zenodo record).

## 5. `cdvqa_sample/` — real change-detection QA text, **no images**

**What's here:** a manifest of real question/answer/image-reference JSON
from the official
[YZHJessica/CDVQA](https://github.com/YZHJessica/CDVQA) GitHub repo
(validation split, first 40 entries of each file).

**What's missing, and why:** CDVQA's repo publishes only
`{Train,Val,Test,Test2}_{questions,answers,images}.json` — there is no
image asset and no download link in the repo, its README, or the paper's
supplementary material. The underlying bi-temporal imagery comes from the
SECOND change-detection dataset, which is distributed on an author-request
basis, not a public direct-download URL. We did not fabricate placeholder
images to fill this gap. Practical effect: the "benchmark reference answer"
UI feature (showing CDVQA's real ground-truth answer next to SatQuery's own
answer for the same image pair) is wired to display whenever a loaded
sample carries `benchmark_reference`, but the shipped sample gallery has no
CDVQA entries with images — the manifest is kept for documentation and so
the schema/UI path is exercised and ready the moment real CDVQA imagery
becomes available.

**License:** Apache-2.0 (per the CDVQA repo's LICENSE file).

## Re-running the fetch

```bash
cd backend
source venv/bin/activate
pip install datasets huggingface_hub pandas pyarrow pillow numpy
python scripts/fetch_data.py            # all five sources
python scripts/fetch_data.py bigearthnet vrsbench   # only specific sources
```

Tunable sample sizes live as constants at the top of `fetch_data.py`
(`BEN_TARGET_PATCHES`, `EUROSAT_PER_CLASS`, `VRSBENCH_TARGET`,
`RSVQA_TARGET`). All five steps together take a few minutes and download on
the order of 150-200MB total (the RSVQA `Images_LR.zip` at ~95MB dominates;
everything else is fetched via ranged/streamed reads well under that).
