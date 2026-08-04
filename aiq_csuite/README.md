# AiQ assessment (Tamara-styled, Gemini or local Ollama)

Private prototype: a **~10 minute** self-serve **AiQ** conversation. Uses **Flask + SQLite/Postgres** for sessions and a **separate admin view** for transcript, timing, and tab-visibility beacons. The LLM (see below) runs the dialogue, a lightweight RAG file (`knowledge/aiq_context_rag.md`), a **scenario randomizer** per session, a **“generic AI”** check (heuristics or optional model), and a **final JSON scoring** pass (D1–D6 and composite AiQ).

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
- **LLM check:** `GET /api/health` or `GET /api/health/llm` (shows `backend`: `gemini` | `openai` | `ollama` | `error`, plus `detail`).
- **APIs:** `POST /api/session/start`, `POST /api/session/<id>/message`, `POST /api/session/<id>/complete`, `POST /api/session/<id>/event`.

**LLM choice (env):** `AIQ_LLM_PROVIDER=openai` (default) uses **OpenAI** if `OPENAI_API_KEY` is set, else **Gemini** if `GOOGLE_API_KEY` / `GEMINI_API_KEY` is set, else **Ollama** at `OLLAMA_BASE` (default `http://127.0.0.1:11434`) if the server is up. Set `AIQ_LLM_PROVIDER=ollama` / `gemini` / `openai` to force. **Ollama (no API key):** [install Ollama](https://ollama.com), `ollama pull llama3.2` (or set `OLLAMA_MODEL`), run `ollama serve`, then with no cloud key uses local inference.

**Model:** Two settings, because the two workloads differ. `AIQ_OPENAI_MODEL` (default
`gpt-5.4-mini`) runs the live interview turns, where a participant is waiting — measured at
~2s/turn, the same as the old `gpt-4o-mini` default but holding one question per turn and
delivering the scenario twist in character instead of announcing it. `AIQ_OPENAI_SCORING_MODEL`
(defaults to the interview model) runs end-of-session scoring and the report: one batch call
behind a progress screen, so a slower, stronger model is affordable there. Validate any
scoring-model change against `scripts/run_scoring_validation.py` first — it shifts every
participant's numbers, and a single transcript cannot tell you whether it shifted them the
right way.

The OpenAI client adapts to whatever parameters a model accepts (newer models reject
`max_tokens` and custom `temperature`), learning per-model at runtime rather than matching on
name prefixes, so a new model generation does not break the app on release day. If OpenAI key is missing, it falls back to `gemini-2.5-flash` (Gemini). **429 / rate limits / quota:** With **Ollama running** (`ollama serve` + `ollama pull` your `OLLAMA_MODEL`), the app **falls back to local** if OpenAI/Gemini returns 429 (interviewer, scoring, and optional paste classifier). You can also remove keys or set `AIQ_LLM_PROVIDER=ollama` to use only Ollama. Paste-detection uses **heuristics** by default (`AIQ_LLM_CLASSIFY=0`) so the LLM only gets one main call per message.

**Database backend (env):**
- Default (no `DATABASE_URL`) → local SQLite at `AIQ_SQLITE_PATH` / `instance/aiq_csuite.db`.
- Set `DATABASE_URL=postgresql://...` (Supabase/Neon/etc) → app uses Postgres for sessions/messages/events.
- One-off migration from existing SQLite file:
  ```bash
  DATABASE_URL='postgresql://...' python3 scripts/migrate_sqlite_to_postgres.py
  ```

**Supabase / PostgREST security:** Tables live in `public`, so Supabase’s Data API can see them unless locked down. On every `init_db()` with Postgres, the app **enables Row Level Security** on `sessions`, `messages`, and `events` (no permissive policies ⇒ **default deny** for `anon` / `authenticated`). Your server uses the **`postgres` DB role** from `DATABASE_URL`; as **table owner** it **bypasses RLS**, so Flask behaviour is unchanged. For **existing** projects created before this change, run `sql/supabase_harden_aiq_tables.sql` once in the Supabase SQL Editor (or trigger any deploy that runs `init_db`). Do **not** expose the Supabase **anon** key in a public browser app pointed at these tables unless you add explicit, reviewed RLS policies.

## Assessment model (four roles)

A session places one person in one realistic work scenario, interviews them on how they'd
handle it, and scores the transcript across six dimensions (D1 awareness, D2 prompts,
D3 critical judgment, D4 workflows, D5 craft, D6 risk) into a weighted **AiQ 0–100** and a
maturity band. It is framed as coaching, not a hiring gate.

**Interview shape.** Scenarios in the four-role pool carry a fixed spine, held by the
server (`conversation_engine`), not by the model's discretion:

1. **Inputs** — what they actually put into the tool, and what they hold back.
2. **Output** — what they asked for, and what came back before they edited it.
3. **Validation** — what happens between the draft and its audience.
4. **The twist** — a confident-but-wrong result, sprung *only* after all three are
   answered, because it only tests verification if they have already committed.
5. Team-norms question, then a warm wrap.

Each is asked one at a time, in the interviewer's own words. A beat the participant
dodges twice is force-advanced so one evasive area can't starve the twist; the 12-turn
cap always wins.

**Scenario pools and retakes.** Strategy & Ops carries **6** variants, deliberately spread
across verticals (operational, Commercial, Personal Banking, Business Banking) because S&O
roles are vertical-agnostic. Each Care role carries **3**. Pool size *is* the retake cap:

- Selection is deterministic from the participant key plus attempt number, so a person who
  abandons and restarts attempt 1 sees the **same** scenario.
- A retake always rotates to a variant they have not seen, so a second attempt measures the
  verification habit rather than memory of a specific twist.
- An attempt only burns a variant once it produced a report — abandoned and timed-out
  sessions don't count.
- Once every variant is served, `POST /api/session/start` returns **409
  `retake_pool_exhausted`** and retakes pause until new variants ship.
- Every session records its attempt number and every report states it, so comparisons
  across people or over time can separate first attempts from retakes.

Participants are recognised by a browser-local `participant_key`; it is not an account. If
storage is cleared the next session is simply treated as a first attempt and nothing is
capped.

**Weights** are computed in code, never invented by the model: a base profile plus additive
deltas for seniority, job family, and the specific function, renormalised to sum 1.0
(`assessment_profiles.py`). The composite is recomputed server-side as
`10 × Σ wᵢ·Dᵢ` and the band derived from it, so a 25-point and an 80-point transcript can't
both read "AiQ3". Published IC weight tables are pinned by `tests/test_assessment_weights.py`
— if a delta is retuned, that test fails and the published table has to move with it.

## Tests

```bash
cd aiq_csuite
.venv/Scripts/python -m pytest tests/ -q     # Windows; use .venv/bin/python elsewhere
```

Scoring quality (needs a live LLM) is exercised separately by
`scripts/run_scoring_validation.py`.

## Production notes

- **Secrets:** Never check `.env` in. Set `AIQ_ADMIN_SECRET` to a long random value. Optional: `AIQ_ADMIN_SECRETS` to allow multiple admin codes (comma/semicolon/newline separated).
- **Network:** Expose only behind your VPN, SSO, or IP allow list.
- **PII:** The COO is identified only by `session_id` in the admin UI unless you add a field.
- **Cost (OpenAI/Gemini):** With heuristics for paste-detection, one model call per user message; completion adds scoring. `AIQ_LLM_CLASSIFY=1` adds an extra call per user message. **Ollama** has no per-token cost (local).

## Files

- `knowledge/aiq_context_rag.md` – rubric, weights, executive expectations (edit here to change RAG without code).
- `knowledge/scenario_library.json` – every scenario: setup, stakes, the three-question ladder, the twist, and what each variant is gauging. **Scenario copy lives here, not in code.**
- `knowledge/scenario_variants.json` – one random hook per dimension per session.
- `assessment_profiles.py` – dimension weights (base × level × family × function) and the scoring profile handed to the model.
- `llm_service.py` – model calls (OpenAI primary; Gemini/Ollama fallbacks): variation, opening, paste classifier, transcript scoring, composite/band enforcement.
- `conversation_engine.py` – LLM-driven interview turns; owns the question ladder and holds the twist until it has been earned.
- `scenario_engine.py` – scenario pools, retake rotation, and the post-session evidence → scores → narrative pipeline.
- `db.py` – DB adapter (SQLite or Postgres via `DATABASE_URL`).
- `sql/supabase_harden_aiq_tables.sql` – one-shot RLS + revoke for Supabase (also applied automatically from `init_db()` on Postgres).
- `scripts/migrate_sqlite_to_postgres.py` – one-off copier from local SQLite to Postgres.
