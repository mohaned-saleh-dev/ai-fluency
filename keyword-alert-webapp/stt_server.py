"""
Serves the Keyword Alert UI and POST /api/transcribe.

Transcription backends (first match wins):
  1) OpenAI Whisper API — set OPENAI_API_KEY (usage billed by OpenAI).
  2) Local Whisper — install `faster-whisper` (see requirements-local.txt); no API key,
     runs on your CPU/GPU. First run downloads the model (cached).

Run from this directory:

  uvicorn stt_server:app --host 0.0.0.0 --port 8765

Free local setup (no OpenAI):

  pip install -r requirements.txt -r requirements-local.txt
  # Optional: brew install ffmpeg   (helps decode browser WebM on macOS)
  uvicorn stt_server:app --host 0.0.0.0 --port 8765

Env (optional):
  WHISPER_MODEL   — default "base" (tiny/base/small/medium; larger = better & slower)
  WHISPER_DEVICE  — default "cpu" (use "cuda" if you have NVIDIA + CUDA)
  WHISPER_COMPUTE — default "int8" for CPU; try "float16" on GPU
"""

from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from openai import OpenAI

BASE = Path(__file__).resolve().parent
_key = os.environ.get("OPENAI_API_KEY", "").strip()
client = OpenAI(api_key=_key) if _key else None

app = FastAPI(title="Keyword Alert STT")

_local_model = None


def _faster_whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def _get_local_model():
    global _local_model
    if _local_model is None:
        from faster_whisper import WhisperModel

        model_name = os.environ.get("WHISPER_MODEL", "base").strip() or "base"
        device = os.environ.get("WHISPER_DEVICE", "cpu").strip() or "cpu"
        compute_type = os.environ.get("WHISPER_COMPUTE", "int8").strip() or "int8"
        _local_model = WhisperModel(model_name, device=device, compute_type=compute_type)
    return _local_model


def _transcription_backend() -> str:
    if client:
        return "openai"
    if _faster_whisper_available():
        return "local"
    return "none"


@app.get("/api/capabilities")
def capabilities():
    src = _transcription_backend()
    return {
        "whisper": src in ("openai", "local"),
        "source": src,
    }


def _transcribe_openai(raw: bytes, filename: str | None) -> str:
    assert client is not None
    buf = io.BytesIO(raw)
    buf.name = filename or "audio.webm"
    tr = client.audio.transcriptions.create(
        model="whisper-1",
        file=buf,
        language="en",
        prompt="English speech only.",
    )
    return (getattr(tr, "text", None) or "").strip()


def _transcribe_local_file(path: str) -> str:
    model = _get_local_model()
    segments, _info = model.transcribe(
        path,
        language="en",
        vad_filter=True,
    )
    parts = []
    for seg in segments:
        t = (seg.text or "").strip()
        if t:
            parts.append(t)
    return " ".join(parts).strip()


def _transcribe_local_from_bytes(raw: bytes, filename: str | None) -> str:
    suffix = ".webm"
    fn = filename or ""
    lower = fn.lower()
    if lower.endswith(".mp4") or lower.endswith(".m4a"):
        suffix = ".m4a"
    elif lower.endswith(".ogg"):
        suffix = ".ogg"
    elif lower.endswith(".wav"):
        suffix = ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        return _transcribe_local_file(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    raw = await audio.read()
    if len(raw) < 120:
        return {"text": ""}

    if client:
        try:
            text = _transcribe_openai(raw, audio.filename)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e)) from e
        return {"text": text}

    if _faster_whisper_available():
        try:
            text = _transcribe_local_from_bytes(raw, audio.filename)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(e)) from e
        return {"text": text}

    raise HTTPException(
        status_code=503,
        detail=(
            "No transcription backend. Set OPENAI_API_KEY for cloud Whisper, or "
            "install local Whisper: pip install -r requirements-local.txt"
        ),
    )


app.mount(
    "/",
    StaticFiles(directory=str(BASE), html=True),
    name="static",
)
