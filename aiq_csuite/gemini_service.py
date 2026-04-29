import json
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import AIQ_LLM_CLASSIFY, BASE_DIR, GEMINI_API_KEY, GEMINI_MODEL, OLLAMA_MODEL
from ollama_client import ollama_available, ollama_chat, ollama_generate_text, resolve_backend

# Varies first message per session; `opening_id` in variation JSON picks the index.
OPENING_VARIANTS: List[str] = [
    (
        "This is an AiQ assessment — about 10 minutes, focused on your real work with AI, not a survey. "
        "I’ll keep questions short. If a question is confusing, you can always ask me to break it down.\n\n"
        "To start, in a sentence or two: what is your role, and what’s one place where AI is either helping a lot or getting in the way?"
    ),
    (
        "We’re going to have a light conversation to understand how you actually use (or don’t use) AI day to day. "
        "I’ll go one clear question at a time.\n\n"
        "First: what do you do day-to-day, and can you name one work situation where AI has been involved recently — in a good or bad way?"
    ),
    (
        "I’m interested in the real mix of tools and habits, not a single product story. Short answers are fine. "
        "I’ll go one clear question at a time.\n\n"
        "To start: your role in one line — and which AI tools (if any) you actually open in a normal week, plus one kind of work you use them for."
    ),
    (
        "The goal here is a practical picture of AI in *your* job — not generic opinions. I’ll be brief, and you can be too. "
        "Asking for clarification is fine at any time.\n\n"
        "Let’s start with: your role in one line, and one real example of AI touching your work lately (tool, process, or frustration)."
    ),
    (
        "I’ll use this session to see how you think about AI in context: trade-offs, judgment, and habits — not a test with right answers. "
        "We have roughly ten minutes.\n\n"
        "In one or two short answers: your role, and where you’ve most noticed AI affecting how you or your team works (positive or not)."
    ),
    (
        "We’re mapping how AI shows up in real roles like yours. Short back-and-forth, no need to be polished. "
        "If something I say is unclear, just say so and I’ll unpack it before we go on.\n\n"
        "To begin: what is your current role, and one concrete work moment where AI mattered in the last few weeks?"
    ),
]


def _llm_mode() -> Tuple[str, str]:
    """(mode, detail). mode: gemini | ollama | error"""
    return resolve_backend(GEMINI_API_KEY)


def _read_rag() -> str:
    p = BASE_DIR / "knowledge" / "aiq_context_rag.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def build_variation_for_session(client_seed: str) -> dict:
    """Pick one scenario hook per dimension; stable enough per session, different across sessions."""
    raw = (BASE_DIR / "knowledge" / "scenario_variants.json").read_text(encoding="utf-8")
    data = json.loads(raw)
    rng = random.Random(client_seed)
    out: Dict[str, Any] = {f"{k}_theme": rng.choice(v) for k, v in data.items()}
    n = len(OPENING_VARIANTS)
    if n:
        out["opening_id"] = rng.randrange(0, n)
    return out


def _get_model(system_instruction: str):
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(
        GEMINI_MODEL,
        system_instruction=system_instruction,
    )


def _history_to_genai(msgs: List[dict]) -> List[dict]:
    m = [dict(x) for x in msgs if x.get("content")]
    if m and m[0].get("role") in ("model", "ai", "assistant"):
        m = [{"role": "user", "content": "Begin the session. Deliver your opening as the interviewer."}] + m
    out: List[dict] = []
    for row in m:
        r = row.get("role", "user")
        if r in ("ai", "assistant", "model"):
            role = "model"
        else:
            role = "user"
        out.append({"role": role, "parts": row["content"]})
    return out


def _strip_json(s: str) -> str:
    t = s.strip()
    m = re.search(r"\{[\s\S]*\}", t)
    return m.group(0) if m else t


def _trailing_comma_sweep(s: str) -> str:
    t = s.strip()
    t = re.sub(r",\s*([}\]])", r"\1", t)
    return t


def parse_scoring_json_object(text: str) -> dict:
    """
    Parse the AiQ scoring JSON. Handles common model mistakes: trailing commas,
    code fences, smart quotes. Raises json.JSONDecodeError if unrecoverable.
    """
    raw = (text or "").strip()
    for blob in (raw, _strip_json(raw)):
        if not blob:
            continue
        for candidate in (blob, _trailing_comma_sweep(blob)):
            candidate2 = (
                candidate.replace("\u201c", '"')
                .replace("\u201d", '"')
                .replace("\u2018", "'")
                .replace("\u2019", "'")
            )
            if not candidate2:
                continue
            try:
                o = json.loads(candidate2)
                if isinstance(o, dict):
                    return o
            except json.JSONDecodeError:
                continue
    raise json.JSONDecodeError("Could not parse scoring JSON", text or "", 0)


# Optional first line from model, stripped before the user sees the reply (and before DB).
_DIM_BANNER = re.compile(
    r"^\s*\[Dim:\s*D([1-6])\s*[-\u2013\u2014]\s*([^\]]+?)\]\s*",
    re.IGNORECASE,
)


def strip_session_complete_flag(raw: str) -> Tuple[str, bool]:
    """
    Strips a trailing [SESSION_COMPLETE] from the last assistant message (UI hint: user can go to summary).
    """
    if not raw or not str(raw).strip():
        return raw, False
    t = str(raw)
    m = re.search(
        r"\[SESSION_COMPLETE\]\s*$", t, re.IGNORECASE | re.DOTALL
    )
    if not m:
        return raw, False
    rest = t[: m.start()].rstrip()
    return (rest, True) if rest else (t, False)


def parse_dimension_banner(raw: str) -> Tuple[str, Optional[dict]]:
    """
    If the model led with e.g. '[Dim: D3 — Output judgment]', remove it and return
    { "code": "D3", "label": "Output judgment" } for UI.
    """
    if not raw or not str(raw).strip():
        return raw, None
    t = str(raw).lstrip()
    m = _DIM_BANNER.match(t)
    if not m:
        return raw, None
    code, label = f"D{m.group(1)}", (m.group(2) or "").strip()[:100]
    rest = t[m.end() :].lstrip()
    if not rest:
        return raw, None
    return rest, {"code": code, "label": label}


# --- Interviewer post-check: fix truncation, missing question, or praise-only turn ---
FRAG_INCOMPLETE = re.compile(
    r"(?i)(,|\b)\s*(?:how|what|when|where|why|which|who|given)\s*,?\s*$|"
    r"(?i)\bhow (?:do|would|are|is|can|could|should|have|did)\s*,?\s*$"
)
FRAG_PRAISE = re.compile(
    r"(?i)^(that\'?s|this is|good|clear|makes sense|useful|great|helpful|understood)\b"
)
FRAG_EVALUATIVE = re.compile(
    r"(?i)(that\'?s a (very )?(clear|good|sensible|wise|strong|practical|smart) "
    r"|a (very )?clear (decision|call|move|metric)|good (call|move)|i (really )?appreciate|"
    r"(well done|nicely (done|put)|i like how you))"
)


def _visible_interviewer_excluding_dim(raw: str) -> str:
    a, b = parse_dimension_banner(raw)
    if b is None:
        return (raw or "").strip()
    return a.strip() if a else ""


def _interviewer_needs_repair(visible: str) -> bool:
    v = (visible or "").strip()
    if not v:
        return True
    if re.search(r"\[SESSION_COMPLETE\]\s*\Z", v, re.IGNORECASE | re.DOTALL):
        return False
    if FRAG_INCOMPLETE.search(v) or re.search(r"(?i)given that[^.!?\n]{0,200}\Z", v):
        return True
    if re.search(r"(?i)understood\.?\s*given", v) and "?" not in v:
        return True
    if "?" not in v and len(v) > 20:
        return True
    if FRAG_PRAISE.search(v) and "?" not in v and len(v) < 400:
        return True
    if FRAG_EVALUATIVE.search(v) and "?" not in v and len(v) < 500:
        return True
    return False


def _repair_interviewer_reply(partial: str) -> str:
    prompt = f"""The AiQ interviewer line below is broken: cut off mid-sentence, missing a follow-up, or is evaluative praise (e.g. "that's a clear…") with no new question, or a stiff opener like "Understood. Given that…" Rewrite to **one** warm, natural turn.

Output only plain text, no code fences. Rules:
- If a session should end, close with a thank-you, tell them to tap "View results" under the input, then a new line with exactly: [SESSION_COMPLETE]
- Otherwise: include at least one complete question (ending in ?) about their AI use at work. **Do not** rate or judge their past answer (no "that's a great/clear/wise" commentary). A neutral bridge is OK ("Thanks —" / "I hear you —" / "Makes sense —" ) **only** if followed immediately by a question.
- Avoid robotic patterns: "Understood. Given that" / "It sounds like" stacked as a substitute for a real question. Sound like a curious colleague, not a form.
- If the input starts with [Dim: D3 — …], keep that first line, blank line, then body.

Broken partial:
<<<
{partial[:7500]}
>>>
Output only the fixed text:
""".strip()
    mode, err_detail = _llm_mode()
    if mode == "error":
        return partial
    if mode == "ollama":
        o = ollama_generate_text(prompt, temperature=0.12, num_predict=900)
        return (o or partial).strip() or partial
    import google.generativeai as genai

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
    )
    r = model.generate_content(
        prompt,
        generation_config={"temperature": 0.12, "max_output_tokens": 900},
    )
    t = (r.text or partial).strip()
    return t if t else partial


def _postprocess_interviewer_reply(raw: str) -> str:
    """Repair obvious failures before the UI sees the line."""
    t0 = (raw or "").strip()
    if not t0:
        return t0
    if re.search(r"\[SESSION_COMPLETE\]", t0, re.IGNORECASE):
        return t0
    vis = _visible_interviewer_excluding_dim(t0)
    if not _interviewer_needs_repair(vis):
        return t0
    fixed = _repair_interviewer_reply(t0)
    v2 = _visible_interviewer_excluding_dim(fixed)
    if v2 and not _interviewer_needs_repair(v2):
        return fixed
    if fixed and (len(fixed) > len(t0) or "?" in fixed and "?" not in t0):
        return fixed
    return t0


class OllamaFallbackForQuota(Exception):
    """Raised from Gemini path when 429/ResourceExhausted and local Ollama is available."""


def _is_gemini_quota_error(e: BaseException) -> bool:
    s = f"{e}"
    t = f"{type(e).__name__} {e}".lower()
    if "ResourceExhausted" in type(e).__name__:
        return True
    if "429" in s:
        return True
    if "resource exhausted" in t or "exceeded your current quota" in t:
        return True
    if "quota" in t and "exceed" in t:
        return True
    if "resource_exhausted" in t:
        return True
    return False


def _heuristic_paste_likeness(user_text: str) -> Tuple[float, str]:
    t = (user_text or "").strip()
    if len(t) < 40:
        return 0.0, ""
    low = t.lower()
    score = 0.2
    reason = ""
    if "as an ai" in low or "as a language model" in low or (
        "i cannot" in low and "policy" in low
    ):
        return 0.75, "disclaimer phrasing"
    if low.count("furthermore,") + low.count("in conclusion") + low.count("in summary,") >= 2:
        score, reason = 0.65, "templated phrasing"
    if t.count("\n\n") >= 4 and len(t) > 500:
        score = max(score, 0.55)
        reason = reason or "block-structured"
    if len(t) > 1200 and t.count("•") + t.count("-") >= 8:
        score = max(score, 0.5)
        reason = reason or "list-heavy"
    return min(1.0, score), reason or "n/a"


def classify_ai_paste_likeness(user_text: str) -> Tuple[float, str]:
    if not AIQ_LLM_CLASSIFY:
        return _heuristic_paste_likeness(user_text)
    mode, _ = _llm_mode()
    if mode == "error" or (mode == "ollama" and not ollama_available()) or (
        mode == "gemini" and not GEMINI_API_KEY
    ):
        return _heuristic_paste_likeness(user_text)
    prompt = f"""Could this be pasted from a generic LLM: padded structure, no real specifics, buzzword soup?

Return JSON only (no markdown):
{{"likelihood_0_1": <0 to 1>, "reason": "<6 words max>"}}

TEXT:
{user_text[:3500]}"""
    try:
        if mode == "ollama":
            raw = ollama_generate_text(
                "Return only JSON.\n\n" + prompt, temperature=0.1
            )
            o = json.loads(_strip_json((raw or "").strip()))
        else:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel(GEMINI_MODEL)
            try:
                r = model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.1, "max_output_tokens": 200},
                )
            except Exception as ge:
                if _is_gemini_quota_error(ge) and ollama_available():
                    raw = ollama_generate_text(
                        "Return only JSON.\n\n" + prompt, temperature=0.1
                    )
                    o = json.loads(_strip_json((raw or "").strip()))
                else:
                    raise
            else:
                o = json.loads(_strip_json((r.text or "").strip()))
        h = _heuristic_paste_likeness(user_text)
        g = float(o.get("likelihood_0_1", 0))
        return max(g, h[0] * 0.9), str(o.get("reason", ""))[:120] or h[1]
    except Exception:
        return _heuristic_paste_likeness(user_text)


def _send_chat_with_retry(
    system: str, history_h: list, user_message: str, max_tries: int = 3
) -> str:
    import google.generativeai as genai
    last_err: Optional[Exception] = None
    for attempt in range(max_tries):
        try:
            genai.configure(api_key=GEMINI_API_KEY)
            model = _get_model(system)
            chat = model.start_chat(history=history_h)
            r = chat.send_message(
                user_message,
                generation_config={"temperature": 0.45, "max_output_tokens": 2048},
            )
            return (r.text or "").strip()
        except Exception as e:
            last_err = e
            if _is_gemini_quota_error(e) and ollama_available():
                raise OllamaFallbackForQuota() from e
            if _is_gemini_quota_error(e):
                time.sleep(2.0 * (attempt + 1))
                continue
            raise
    if last_err:
        raise last_err
    return ""


def run_interviewer_reply(
    rag_text: str,
    variation: dict,
    history_ui: List[dict],
    user_message: str,
    context_note: str,
) -> str:
    """One assistant turn. One clear question; allow brief follow-up if the user is clarifying their last point."""
    from assessment_profiles import interviewer_profile_note

    v_private = " ".join(
        f"[{k}] {v}" for k, v in sorted(variation.items(), key=lambda x: x[0]) if k != "assessment"
    )
    assm = (variation or {}).get("assessment") if isinstance(variation, dict) else None
    profile_note = interviewer_profile_note(assm)
    jslug = str((assm or {}).get("job_family") or "").strip()
    if jslug == "risk_legal":
        reg_note = "Job family: **risk, legal, compliance** — you may go **deeper** on policy, evidence, and vendor/regulator *when* it fits the chat. Still avoid a generic RFP monologue; ground questions in *their* remit."
    else:
        reg_note = (
            "**D6 (responsible use) is still for *every* role:** everyday habits, sensitive data, escalation, no-go zones — the same *spirit* as org-wide **security, data, AML** training, at *their* altitude. "
            "**But** this job family is *not* default to deep vendor or regulator *essay* questions — reserve **long** due-diligence / **named** regulatory framing (e.g. multi-party vendor “posture” homework) for when the participant *has* raised it or clearly owns that work, not for cold open. "
            "See the session calibration line on D6 and depth pair."
        )
    _prefix = (profile_note + "\n\n") if profile_note else ""
    system = f"""{_prefix}You run a **short, human AiQ conversation** — a **curious, respectful, friendly** peer chat (think: a thoughtful colleague over coffee), **not** a deposition, **not** an audit, **not** a training session, **not** a place to teach "best practice." The participant’s **level and job family** are in the session calibration; do not assume they own operational minutiae.

{reg_note}

**Tone & social contract (strict):**
- **Warm, courteous, and natural:** varied sentence openers, plain language, a human pace. **Avoid** stiff lead-ins like "Understood. Given that…" or stacked formal transitions — say what you need in a friendly, direct way.
- **Not investigative:** you are *not* testing whether they "know enough" or catching them out. If an answer is thin, assume good intent (busy day, NDA, or a topic that does not excite them). **Do not** cross-examine, stack rapid follow-ups, or imply judgment.
- **No opinions on the quality of their decisions:** do **not** say things like "That’s a very clear / wise / good decision" or "That’s a clear metric" as commentary — that adds little and sounds robotic. You may use a **one-breath neutral bridge** ("Thanks —", "I hear you —", "Makes sense —") **only** to move into the next question, not to evaluate them.
- **Give the benefit of the doubt:** if they have mentioned **several** AI use cases or tools but can’t (or don’t) go deep on the one you asked, **do not** keep pressing on the same line. After **at most one** gentle rephrase, **pivot with grace** to another use case, tool, or work stream they *already* named, e.g. "We can keep this light — I’m also curious about [X you mentioned]…" or "Happy to switch angles: is there a different part of the week where AI actually shows up more for you?"
- **Never** lecture, moralize, or explain *why* something is "important" in a corporate-training voice. No mini-lessons, no "Without X you risk…"
- **Ask** out of genuine curiosity at the **right altitude** — narrative, trade-offs, how they think, what they need from others — not a pop quiz. Offer an **out** ("e.g.…", "broadly…") when asking for detail.
- **Early turns:** keep questions **broad and human**; save heavier risk/governance depth for when you have context. If they ask you to **clarify** your question: rephrase in plain language, then **one** simple question.

**Format:**
- **One** main question per turn, **one** sentence as the default; optional **second short sentence** only to clarify. Under ~90 words unless they only asked for clarification (then under ~100).
- **Quality gate (mandatory):** on every turn until the closing turn, the visible message must include a **complete question** in full sentences (using **?**) about their AI *use, judgment, or how they work with models*. Do not end with only a metric, label, or compliment — e.g. "That's a clear metric" must be followed by a follow-up question in the *same* message. Do not leave phrases like "how" or "how do" **unfinished**.
- Plain text. No "Assistant:". No bullet lists. No "labels" in speech like "From a governance perspective…" as a filler.

**Depth / follow-up limit (strict):**  
- On the *same* user turn, at most **2** of your follow-up questions before you **change angle** (new hook or another dimension) — *not* seven nested refinements.  
- Within the *same* AiQ dimension, at most **3** of your questions total before you move breadth-wise (unless the user is still only clarifying your wording).  
- Do not chain long “part (a) / part (b) / part (c)” scaffolds; one clear question, then let them answer.

**Tooling & stack (maps to D1 *Awareness & opportunity* + D2 *Prompts & comms* — not a separate “seventh” score, but a required line of evidence):**  
- By the **mid-point of the session** (several turns in), you must have a working picture of **which** generative-AI or copilot tools they use in *real* work (product names and surfaces are fine) and **what they use them for** (e.g. drafts, code, research, comms, analysis). If they only name one, ask once for **another** tool or workstream that uses AI — unless they truly have a single tool, in which case pivot to judgment, risk, or workflow.  
- **Do not** let most of the conversation stay on the **same** product, project code name, or internal feature. If the participant’s last **two** answers keep circling the **same named** product, your **next** question must **widen the lens** (other tool, other workstream, or leadership / hand-off / risk angle) so the session is not a deep dive on one line item.  

**Closing the interview (the app can always show a summary) — *mandatory* behavior:**  
- **Never** say you cannot show results, scores, or a summary, or that your role is only to block output. The page has **“View results”** below the input; it opens a one-page read from *this* chat. If they ask for results, say: tap **“View results”** under the input — that is how they see the one-page view from this session.  
- When you have no further main questions, thank them briefly, **one** short sentence telling them to tap **“View results”** under the input, then a **separate** final line **exactly**: `[SESSION_COMPLETE]` (app-only, not spoken aloud; user will not be asked to type it).  
- **Do not** stop after a cold “That’s all for today” with no next step.

**Dimension hand-off (for the app UI, only on a *real* change of angle):**  
If and **only** if this reply is the first time in this session you are deliberately probing a *different* AiQ dimension than the **immediately previous model turn**, put a **single first line** exactly in this form, then a blank line, then your question:  
`[Dim: D2 — <short name>]`  
Use these short names only: D1 *Awareness & opportunity*, D2 *Prompts & comms*, D3 *Critical judgment*, D4 *Workflows & org design*, D5 *Clarity, craft & output fit*, D6 *Risk & responsible use.*  
**If you are still in the *same* dimension as last turn (e.g. both turns are D3), you must *omit* the `[Dim: …]` line entirely** — no duplicate banners, no re-announcement of the same label. If unsure, **omit** the line.
- **Role fit (COO / exec default):** Do **not** fall into contact-center, “agent QA,” or “the AI that scores support chats” framing **unless** the participant has already said they own that surface. Default to **P&L, org design, portfolio, board / leadership trade-offs, and how they set expectations for others**. For D3 evidence, ask for a **concrete leadership moment** (pushback, trade-off, “we said no because…”) — not a generic “name an AI output you would challenge in the abstract” homework exercise. Keep early questions **one level up** from frontline ops minutiae.

**What this session is (non-negotiable) — *AiQ* = AI *fluency* in *their* work:**  
- Every main question in your next reply must be **obviously and directly** about how they **use, direct, challenge, or govern *generative AI or AI-assisted tools*** (models, copilots, automations, AI features in product/workflow) **in the context of that job**. The listener should not wonder whether this is a “general process interview.”  
- **Off-limits (unless the user already said it in this chat):** human **QA of agents**; **human** reviewers of chat logs; how “**AI chatbot**” products are **trained for customers**; “performance evaluation” of **people** with no model in the room; “organizational process improvement” with no link to **their** AI use. If a scenario hook or your own phrasing drifts there, **rewrite the question** so the core asks about *their* judgment, prompts, ownership, or risk *when a model is in the loop*.  
- **Test before you send:** If you could ask the same question in a 2010 interview and nothing would change, it is **wrong** — it must name or clearly imply **AI/LLM/model/copilot/GenAI, prompt, or model output** in the *participant’s* work.  
- **One** question, **not** a stack of sub-questions about a process.
- {context_note}

**Scenario hooks (internal only; must become AI-fluency questions):**  
The lines below are **vignettes to bend toward GenAI in *their* role** — *not* permission to ask about *QA teams*, *contact centers*, or *chat-agent roadmaps* unless the participant has already said they work there. {v_private[:2000]}

RAG (weights and dimensions — **internal** only; do not name RAG, codes, or "dimensions" to the user):
{rag_text[:8000]}

Over **roughly 10–15 minutes**, you want *breadth* across the six areas in the RAG without making it feel like an interrogation or a checklist. You **never** say "D1" or "dimension" aloud."""

    mode, err_detail = _llm_mode()
    if mode == "error":
        raise RuntimeError(err_detail)
    h = _history_to_genai(history_ui)
    if mode == "ollama":
        return _postprocess_interviewer_reply(
            ollama_chat(system, history_ui, user_message, temperature=0.45)
        )
    try:
        out = _send_chat_with_retry(system, h, user_message)
    except OllamaFallbackForQuota:
        out = ollama_chat(system, history_ui, user_message, temperature=0.45)
    except Exception as e:
        if not _is_gemini_quota_error(e) or not ollama_available():
            if _is_gemini_quota_error(e) and not ollama_available():
                raise RuntimeError(
                    f"Gemini quota or rate limit ({e!s}) — set up local Ollama: "
                    f"install from https://ollama.com, then: ollama pull {OLLAMA_MODEL} && ollama serve, "
                    "or fix billing in Google Cloud / AI Studio."
                ) from e
            raise
        out = ollama_chat(system, history_ui, user_message, temperature=0.45)
    return _postprocess_interviewer_reply(out)


def opening_message(variation: dict) -> str:
    i = int(variation.get("opening_id", 0) or 0) % max(1, len(OPENING_VARIANTS))
    return OPENING_VARIANTS[i]


def _score_with_ollama_from_prompt_body(prompt: str) -> dict:
    full = (
        "You are a strict assessor. Return only a single JSON object, no markdown, no prose before or after.\n\n"
        + prompt
    )
    r1 = ollama_generate_text(full, temperature=0.2)
    try:
        return parse_scoring_json_object(r1)
    except json.JSONDecodeError:
        pass
    r2 = ollama_generate_text(
        "Return raw JSON only (no backticks, no newlines inside string values).\n\n" + prompt,
        temperature=0.1,
    )
    try:
        return parse_scoring_json_object(r2)
    except json.JSONDecodeError:
        pass
    r3 = ollama_generate_text(
        "The previous model output was invalid. Output ONLY a single valid JSON object with the same "
        "keys: D1..D6, AiQ_0_100, maturity_band, strength_1line, risk_1line. "
        "Every string: one line, no double quotes inside, max 200 chars. Invalid output:\n\n"
        + (r1 or "")[:8000],
        temperature=0.1,
    )
    return parse_scoring_json_object(r3)


# Rationales shown in the one-page report must not read as internal assessor notes.
_RE_ASSESSOR_VOICE = re.compile(
    r"(\bthe user\b|"
    r"\bthe participant\b|"
    r"\bthe interviewee\b|"
    r"preventing assessment\b|"
    r"no information beyond|"
    r"(?:only|merely) (?:their|the) job title|"
    r"did not (?:provide|share|give|offer)\b|"
    r"failed to (?:provide|share|give|offer)\b|"
    r"insufficient (?:information|data|content|evidence|detail)\b.*\bassess|"
    r"cannot (?:assess|evaluate) (?:because|due|with)|"
    r"not enough (?:information|data|detail) (?:to|for) (?:assess|anchor))",
    re.IGNORECASE,
)
_FALLBACK_DIM = (
    "Snapshot from this short chat: lighter weight here means fewer concrete details "
    "showed up in the thread, not a personal judgment."
)
_FALLBACK_STRENGTH = (
    "A quick, directional read from the conversation, useful for reflection, not a final grade."
)
_FALLBACK_RISK = (
    "Directional only: more specific examples in a follow-up would sharpen the picture."
)


def _sanitize_rationale_line(s: str, fallback: str) -> str:
    t = (s or "").strip()
    if not t:
        return fallback
    if _RE_ASSESSOR_VOICE.search(t):
        return fallback
    return t


def sanitize_scoring_for_participant_view(out: dict) -> dict:
    """
    Replace model-generated assessor-only phrasing in fields shown on the one-page report.
    Numbers are unchanged; only string rationales and summary lines.
    """
    if not isinstance(out, dict):
        return out
    o = dict(out)
    for i in range(1, 7):
        k = f"D{i}"
        b = o.get(k)
        if not isinstance(b, dict):
            continue
        b2 = dict(b)
        r = b2.get("rationale_1line")
        if not isinstance(r, str):
            continue
        b2["rationale_1line"] = _sanitize_rationale_line(r, _FALLBACK_DIM)
        o[k] = b2
    s0 = o.get("strength_1line")
    o["strength_1line"] = _sanitize_rationale_line(
        s0 if isinstance(s0, str) else "", _FALLBACK_STRENGTH
    )
    r0 = o.get("risk_1line")
    o["risk_1line"] = _sanitize_rationale_line(
        r0 if isinstance(r0, str) else "", _FALLBACK_RISK
    )
    return o


def _finalize_scoring_for_session(out: dict, weights: Optional[dict]) -> dict:
    return sanitize_scoring_for_participant_view(
        _apply_session_weights_to_composite(out, weights)
    )


def _apply_session_weights_to_composite(
    out: dict, weights: Optional[dict]
) -> dict:
    """Enforce AiQ_0_100 = 10 * Σ w_i * D_i (D_i on 0–10). Source of truth: code + session weights."""
    if not isinstance(out, dict) or not weights:
        return out
    s = 0.0
    for i in range(1, 7):
        key = f"D{i}"
        wv = float(weights.get(key, 0.0) or 0.0)
        sc = out.get(key) or {}
        dv = float(sc.get("score", 0) or 0) if isinstance(sc, dict) else 0.0
        s += wv * dv
    out["AiQ_0_100"] = round(10.0 * s, 1)
    return out


def score_transcript(msgs: List[dict], variation: dict) -> dict:
    """Return dimension scores, composite AiQ, and band."""
    from assessment_profiles import default_assessment, scoring_context_block

    mode, err_detail = _llm_mode()
    if mode == "error":
        raise RuntimeError(err_detail)
    rag = _read_rag()
    v = variation or {}
    ass = v.get("assessment")
    if not ass or not isinstance(ass, dict) or not ass.get("weights"):
        ass = default_assessment()
    w = ass.get("weights") or {}
    w1, w2, w3, w4, w5, w6 = (w.get(f"D{i}", 0.0) for i in range(1, 7))
    sctx = scoring_context_block(ass)
    transcript = []
    for m in msgs:
        role = m.get("role", "")
        if role == "user":
            label = "USER"
        else:
            label = "ASSISTANT"
        transcript.append(f"{label}: {m['content']}")
    t_text = "\n\n".join(transcript)[-100000:]

    them = {k: val for k, val in v.items() if str(k).endswith("_theme")}
    prompt = f"""Score this AiQ *conversation* transcript. You **must** apply the assessment profile below when judging evidence. Each dimension 0-10 in 0.5 steps.

{sctx}

RAG (shared definitions; interpret through the profile above):
{rag}

TRANSCRIPT:
{t_text}

Session scenario themes (context only): {json.dumps(them)}
"""
    prompt += f"""
Return **one** JSON object only, **no** markdown, **no** code fences, **no** keys except those below. Maturity band must be one of: AiQ1, AiQ2, AiQ3, AiQ4.
{{
  "D1": {{"score": 0, "rationale_1line": ""}},
  "D2": {{"score": 0, "rationale_1line": ""}},
  "D3": {{"score": 0, "rationale_1line": ""}},
  "D4": {{"score": 0, "rationale_1line": ""}},
  "D5": {{"score": 0, "rationale_1line": ""}},
  "D6": {{"score": 0, "rationale_1line": ""}},
  "AiQ_0_100": 0,
  "maturity_band": "AiQ3",
  "strength_1line": "",
  "risk_1line": ""
}}

**Rules that prevent broken JSON (mandatory):**
- Every `rationale_1line`, `strength_1line`, and `risk_1line` must be **one** short line, **no** newlines, **no** unescaped **double-quote** characters. Use only letters, digits, space, and basic punctuation (- ; ' . ,). If you need emphasis, rephrase; do not use a period chain that breaks strings.
- Every string value under 200 characters.

**Report copy (read by the interviewee; mandatory):**  
All `rationale_1line`, `strength_1line`, and `risk_1line` are shown to the person who was interviewed. Write in **neutral, respectful** language, or with **you** if natural (e.g. you described, this exchange stayed high-level). Describe limits of **the chat**, not moral failure.  
**Never use:** the phrases *the user*, *the participant*, *preventing assessment*, *insufficient to assess* as blame, *did not provide* (in an accusatory way), *only* their *job title* as a critique, or any line that sounds like an internal grading memo.

Recompute AiQ_0_100 = 10 * ({w1}*D1 + {w2}*D2 + {w3}*D3 + {w4}*D4 + {w5}*D5 + {w6}*D6) using the numeric D scores, rounded to 1 decimal. These weights are **fixed** for this session. Rationales: one short clause; avoid niche regulatory acronyms or vendor diligence unless the job family is risk/legal. Do not return markdown.
"""
    if mode == "ollama":
        out = _score_with_ollama_from_prompt_body(prompt)
        return _finalize_scoring_for_session(out, w)
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(
        GEMINI_MODEL,
        system_instruction=(
            "You are a strict assessor. Output only valid JSON. Rationales and one-line "
            "summaries are read by the person interviewed: neutral or second person, never "
            "'the user' or third-person internal grading notes."
        ),
    )
    try:
        r = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 2500,
                "response_mime_type": "application/json",
            },
        )
    except Exception as e:
        if not (_is_gemini_quota_error(e) and ollama_available()):
            if _is_gemini_quota_error(e) and not ollama_available():
                raise RuntimeError(
                    f"Gemini quota on scoring — install Ollama, run ollama pull {OLLAMA_MODEL} && ollama serve, "
                    f"or try again later. {e!s}"
                ) from e
            raise
        return _finalize_scoring_for_session(
            _score_with_ollama_from_prompt_body(prompt), w
        )
    t0 = r.text or ""
    try:
        out = parse_scoring_json_object(t0)
    except json.JSONDecodeError:
        t_fix = t0
        t2: Optional[str] = None
        try:
            r2 = model.generate_content(
                "The previous model output was not valid JSON. Return ONLY one JSON object, same keys as before "
                "(D1..D6 with score and rationale_1line, AiQ_0_100, maturity_band, strength_1line, risk_1line). "
                "Every string value: one line, no double quotation marks inside, max 200 characters. "
                "No markdown, no text outside the JSON. Invalid output:\n\n" + t_fix[:12000],
                generation_config={
                    "temperature": 0.1,
                    "max_output_tokens": 4000,
                    "response_mime_type": "application/json",
                },
            )
            t2 = (r2.text or "").strip()
        except Exception as ge2:
            if ollama_available():
                out = _score_with_ollama_from_prompt_body(prompt)
                return _finalize_scoring_for_session(out, w)
            raise RuntimeError(
                f"Scoring repair call failed: {ge2!s}"
            ) from ge2
        try:
            out = parse_scoring_json_object(t2)
        except json.JSONDecodeError:
            if ollama_available():
                out = _score_with_ollama_from_prompt_body(prompt)
            else:
                raise RuntimeError(
                    "Scoring returned data we could not read as JSON. Please tap “View results” again; "
                    "if it repeats, the model may need a retry or a local Ollama fallback for scoring."
                ) from None
    return _finalize_scoring_for_session(out, w)


def get_rag_for_app() -> str:
    return _read_rag()
