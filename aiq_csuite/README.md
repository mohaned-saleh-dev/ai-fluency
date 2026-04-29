# AiQ assessment (Tamara-styled, Gemini or local Ollama)

Private prototype: a **~10 minute** self-serve **AiQ** conversation. Uses **Flask + SQLite** for sessions and a **separate admin view** for transcript, timing, and tab-visibility beacons. The LLM (see below) runs the dialogue, a lightweight RAG file (`knowledge/aiq_context_rag.md`), a **scenario randomizer** per session, a **“generic AI”** check (heuristics or optional model), and a **final JSON scoring** pass (D1–D6 and composite AiQ).

## Branding

UI uses **Visual Identity Guidelines 2025** tokens: Tamara Lavender `#9600F1`, Zingy Purple `#5300BA`, **Plus Jakarta Sans** for type (as in the PDF; licensed *Degular Display* can be dropped in for large headlines if the brand team provides files). The **tamara** white wordmark PNG is in `static/brand/`: use it on **lavender / purple** surfaces, or a small **gradient pill** on white (see `static/brand.css`). Do not use `filter: brightness(0)` to “invert” it—that often renders a black block with PNG alpha.

## Run locally

```bash
cd aiq_csuite
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# For Gemini: set GOOGLE_API_KEY. For local-only: install Ollama, then no API key is required (see “LLM choice” below).
# Set AIQ_ADMIN_SECRET
python app.py
# Open http://127.0.0.1:5020/  and http://127.0.0.1:5020/admin
```

- **Assess:** `/` (HTML + JS).
- **AiQ executive deck — PDF:** `http://127.0.0.1:5020/deck/executive.pdf` — **same slide layout** as the HTML deck (`/deck/executive`), built with **headless Google Chrome** when the binary is on the `PATH` or in the default macOS/ Linux locations. If Chrome is not available, the app falls back to a plain text ReportLab PDF (install `reportlab` via `requirements.txt`).
- **Same deck as Slideshow HTML:** `http://127.0.0.1:5020/deck/executive` (on-screen; PDF route matches this layout when Chrome is present).  
- **Executive memo (long read-ahead):** `http://127.0.0.1:5020/deck/executive-memo`  
- **Source:** `../aiq-executive-summary.html` (v1.2 in cover); copy under `static/deck/`.
- **Admin:** `/admin` opens a login screen; paste an admin code from env and load sessions.
- **LLM check:** `GET /api/health` or `GET /api/health/llm` (shows `backend`: `gemini` | `ollama` | `error`, plus `detail`).
- **APIs:** `POST /api/session/start`, `POST /api/session/<id>/message`, `POST /api/session/<id>/complete`, `POST /api/session/<id>/event`.

**LLM choice (env):** `AIQ_LLM_PROVIDER=auto` (default) uses **Gemini** if `GOOGLE_API_KEY` / `GEMINI_API_KEY` is set, otherwise **Ollama** at `OLLAMA_BASE` (default `http://127.0.0.1:11434`) if the server is up. Set `AIQ_LLM_PROVIDER=ollama` or `=gemini` to force. **Ollama (no API key):** [install Ollama](https://ollama.com), `ollama pull llama3.2` (or set `OLLAMA_MODEL`), run `ollama serve`, then `auto` with no key uses local inference.

**Model / 404 (Gemini):** The app defaults to `gemini-2.5-flash` (2.0-flash and older are often 404 for new users). If you get 404, set `AIQ_GEMINI_MODEL` to a name your key supports, e.g. `gemini-2.5-flash-lite` (see [models](https://ai.google.dev/gemini-api/docs/models)). **429 / rate limits / quota:** With **Ollama running** (`ollama serve` + `ollama pull` your `OLLAMA_MODEL`), the app **falls back to local** if Gemini returns 429 (interviewer, scoring, and optional paste classifier). You can also remove the key or set `AIQ_LLM_PROVIDER=ollama` to use only Ollama. Paste-detection uses **heuristics** by default (`AIQ_LLM_CLASSIFY=0`) so Gemini only gets one main call per message.

## Production notes

- **Secrets:** Never check `.env` in. Set `AIQ_ADMIN_SECRET` to a long random value. Optional: `AIQ_ADMIN_SECRETS` to allow multiple admin codes (comma/semicolon/newline separated).
- **Network:** Expose only behind your VPN, SSO, or IP allow list.
- **PII:** The COO is identified only by `session_id` in the admin UI unless you add a field.
- **Cost (Gemini):** With heuristics for paste-detection, one model call per user message; completion adds scoring. `AIQ_LLM_CLASSIFY=1` adds an extra call per user message. **Ollama** has no per-token cost (local).

## Files

- `knowledge/aiq_context_rag.md` – rubric, weights, executive expectations (edit here to change RAG without code).
- `knowledge/scenario_variants.json` – one random hook per dimension per session.
- `gemini_service.py` – model calls.
- `db.py` – SQLite.
