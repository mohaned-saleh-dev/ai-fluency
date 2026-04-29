# AiQ self-assessment: RAG context (all levels)

## Purpose
Conversational assessment of AI fluency (AiQ). **Six** dimensions, scored 0–10 each, then composite **AiQ 0–100** with the default weights below (suitable for leadership-heavy roles; adjust in code or prompt if you scope to IC-only). The live interviewer aims for a **light pass across all six** angles, then **deeper follow-up** on the **two dimensions with highest weight** for the participant’s level × job family (set in app code). The experience is framed for **reflection and coaching**, not a hiring rank.

## Scoring formula
- Each dimension **D1–D6** is scored **0–10** (integers or half-points at assessor discretion).
- **Composite:** `AiQ = 10 × (w1·D1 + w2·D2 + … + w6·D6)` where weights sum to **1.0**. Maximum **100** when all dimensions are 10/10.
- Maturity **bands (reference only):** AiQ 1: 0–25, AiQ 2: 26–55, AiQ 3: 56–80, AiQ 4: 81–100. C-level **targets** typically sit in the **56–100** range depending on remit; use judgment from evidence, not from title alone.

## C-suite / general executive weights (this experience)
| Code | Dimension | Weight |
|------|-----------|--------|
| D1 | AI awareness & opportunity recognition | 0.16 |
| D2 | Prompt engineering & AI communication | 0.10 |
| D3 | Output evaluation & critical judgment | 0.16 |
| D4 | Workflow design & integration (incl. org / operating model) | 0.20 |
| D5 | Clarity, craft & output fit — AI-supported **outputs others see** (docs, comms, deliverables; GTM may add market narrative) | 0.08 |
| D6 | Responsible AI use (privacy, risk, IP, compliance, vendor posture) | 0.30 |

*Rationale: executives carry disproportionate **risk and governance** load (D6) and must connect AI to **operating model and cross-functional workflows** (D4). D5 is **universal in intent** (everyone has *some* work product that others read), but weight is not primary for most execs vs. P&L, risk, and execution.*

## Dimension focus (what “good” looks like at C-level)
- **D1:** Sees where AI changes unit economics, speed, or risk; differentiates hype vs. durable use cases; prioritization. *In the live interview*, surface **which** AI tools and surfaces they use (e.g. ChatGPT, Copilot, in-house copilots) and for **what** kinds of work — that grounds awareness in practice, not only strategy.
- **D2:** Directs and critiques AI work (briefs, vendors, functions); clear success criteria, constraints, iteration loops—not necessarily hand-authoring every prompt. Connects to **how** they steer the tools in D1 in real work (prompts, defaults, comms) — the conversation should not stay on one product or feature the whole time.
- **D3:** Instinct for review **before** external or regulatory exposure; challenges outputs that are confident but wrong; calibrates human vs. AI judgment.
- **D4:** Embeds AI in cadence, governance, and workflows (e.g. planning, reporting, GTM, people systems); role clarity between human and model.
- **D5:** Quality, **clarity**, and **appropriateness** of model-assisted *outputs that others read or rely on* — from internal specs and email to support replies and, where relevant, **external** narrative. Not “brand” as marketing-only; avoid judging creative taste unless the role is comms- or GTM-heavy.
- **D6:** Data handling, model/vendor choices, third-party access, customer/partner impact, and auditability. **Every** serious role has a *floor* here in the *spirit* of org-wide security and AML-style training; **deeper** regulatory or third-party *diligence* is role-dependent. Willing to say no.

## “Solution architecture” probe (for Tamara or similar regulated fintech)
Expect credible discussion of: data boundaries, environments, evaluation of vendor vs. in-house, controls for PII, human review for high-risk decisions, monitoring and incident thinking. Map answers back to D2–D4 and especially **D6**.

## Tooling & variety in the *conversation* (not an extra score)
- The interviewer should learn **which tools** they use and **for what** (feeds D1/D2) without running the whole session as a **single** product or feature case study. If the participant reuses the same example, shift angle (another tool, another workstream, another stakeholder).

## Anti-patterns
- Vague “we use AI to be more efficient” with no trade-offs.
- Unbounded outsourcing of judgment to a model.
- Inability to describe where human review is mandatory.
- All strengths and no material risks (lack of D3/D6).
