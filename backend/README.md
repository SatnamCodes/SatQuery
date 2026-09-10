# SatQuery AI — backend

FastAPI service exposing the orchestrator, the deterministic CV pipeline
(change detection, segmentation, fusion, grounding), and the sample data
catalog. See `../frontend/README.md` for the UI, `data/README.md` for
dataset provenance.

## Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit .env — see below
uvicorn app.main:app --reload --port 8811
```

## Narration backends

SatQuery's narration layer (`app/services/vlm.py`) can run against either:

- **Gemini** (cloud) — set `GEMINI_API_KEY`. This is what the deployed demo
  uses. Free-tier Gemini has a rate limit; once it's hit, `/api/query`
  responses say so explicitly instead of failing silently.
- **Ollama** (local) — no API key, no rate limit, runs on your own GPU.
  Install [Ollama](https://ollama.com), then:
  ```bash
  ollama pull qwen2.5vl:7b
  ```
  Set `SATQUERY_VLM_BACKEND=ollama` in `.env` (or leave it on `auto` and
  simply unset `GEMINI_API_KEY` — auto mode prefers Gemini when a key is
  present, and falls back to Ollama otherwise).

Everything else — change detection, segmentation, optical/SAR fusion,
grounding — runs entirely on deterministic CV (OpenCV) with no external
call and no dependency on either narration backend; that's the
"offline-capable core" the header badge refers to. Narration is the only
piece that needs a model at all.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | unset | Enables the Gemini narration backend |
| `SATQUERY_VLM_BACKEND` | `auto` | `gemini` \| `ollama` \| `auto` |
| `SATQUERY_VLM_MODEL` | `qwen2.5vl:7b` | Ollama model tag |
| `SATQUERY_GEMINI_MODEL` | `gemini-3.6-flash` | Gemini model name |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server address |
| `SATQUERY_CORS_ORIGINS` | `*` | Comma-separated allowed origins in production |

## Deployment

Deployed as a standard Python web service (see repo root `DEPLOY.md`).
The deployed instance uses the Gemini backend — there is no GPU in that
environment, so Ollama only works when you run the backend yourself.
