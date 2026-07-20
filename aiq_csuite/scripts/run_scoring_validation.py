#!/usr/bin/env python3
"""
Phase 1 scoring validation (build-plan section 8): per pilot family, run one transcript
written to look strong and one written weak, at the ic and executive ends, through the real
evidence + scoring pipeline, then confirm — not assume — that:

  1. Strong and weak transcripts produce clearly separated composites, not clustered ones.
  2. Dimension scores are internally consistent (no risk content => D6 must not score high;
     any dimension with zero grounded evidence quotes must sit in the low band).
  3. The composite and maturity band move the way a human reading the transcript would expect.
  4. Every evidence quote returned exists verbatim in the participant's own turns.

Also checks (no LLM) that all 12 pilot level x family combos resolve to the intended
scenario cluster. Usage: python scripts/run_scoring_validation.py [--families f1,f2] [--skip-llm]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import llm_service as gs
import scenario_engine as se
from assessment_profiles import build_assessment_block
from llm_json import llm_mode

PILOT_FAMILIES = ["product_engineering", "go_to_market", "care_operations"]
PILOT_LEVELS = ["ic", "people_manager", "head_of", "executive"]

# Expected scenario cluster per (family, level) — the pilot matrix contract.
EXPECTED_CLUSTERS: Dict[Tuple[str, str], str] = {}
for _lvl in PILOT_LEVELS:
    EXPECTED_CLUSTERS[("go_to_market", _lvl)] = "gtm"
for _lvl in ("ic", "people_manager"):
    EXPECTED_CLUSTERS[("product_engineering", _lvl)] = "product"
    EXPECTED_CLUSTERS[("care_operations", _lvl)] = "ops"
for _lvl in ("head_of", "executive"):
    EXPECTED_CLUSTERS[("product_engineering", _lvl)] = "product_exec"
    EXPECTED_CLUSTERS[("care_operations", _lvl)] = "ops_exec"


# --- Synthetic transcripts -----------------------------------------------------------
# Strong answers show the six behaviors the rubric anchors describe (tools mapped to tasks,
# structured prompting, verification habit, owned workflow, explicit output bar, proactive
# risk floor). Weak answers are engaged enough to pass the effort gate but show none of them.

STRONG_ANSWERS: Dict[str, Dict[str, List[str]]] = {
    "product_engineering": {
        "ic": [
            "Senior product manager on the payments checkout team. Weekly: ChatGPT for spec first drafts and edge-case brainstorming, Copilot in the IDE for review suggestions, and Claude for summarizing long compliance docs. I skipped AI for our fee-calculation logic though — too easy for it to invent a rule that sounds right.",
            "First I'd collect the real inputs: the PRD stub, the current checkout flow doc, and the card-scheme rules PDF. My prompt gives it a role - senior payments PM - pastes those as context, and says output acceptance criteria only, flag anything you are unsure of, do not invent compliance rules. First draft is never final; I iterate twice on average.",
            "I diff every requirement against the scheme rules doc line by line, because ChatGPT once invented a 3DS exemption that didn't exist and I caught it before review. Anything touching money or compliance gets checked against the source, not my memory. My bar: an engineer can build from it without pinging me, and compliance finds zero invented rules.",
            "Kill that shared chat immediately, tell the person no blame, then report it to security the same hour - we have a channel for AI data incidents. Move spec work to the approved enterprise workspace, and re-run the intro rule: real account numbers never go into any model, test fixtures only.",
            "One rule: every AI-drafted spec carries a named human owner who signed off against source docs before engineering sees it. In Jira the spec template literally has an 'AI-assisted, verified by' field we added last quarter.",
            "I'd bring compliance in earlier - drafting with AI is fast enough that the bottleneck is review, so start their read in parallel rather than at the end.",
        ],
        "executive": [
            "VP of engineering, about 120 engineers. I use ChatGPT and our internal copilot daily for board narratives and org design options, Copilot is deployed org-wide with usage dashboards I review monthly. We deliberately did not apply AI to incident postmortems yet - I want unfiltered human accounts there.",
            "Before build-versus-buy I'd force both paths through the same scorecard: total cost over three years, eval results on our own codebase - not the vendor's benchmark - security posture, and exit cost. I'd have two leads run a two-week structured pilot with defined metrics rather than argue in the abstract.",
            "Vendor demos are marketing. I'd require an eval on a frozen sample of our real pull requests, measured on defect catch-rate against our historical bugs, and I'd ask the vendor what happens to our code snippets - retention, training use, tenancy - in writing.",
            "That engineer went around an agreed process, so first the tool access gets suspended, then I want to know why the pilot process felt too slow - usually that's the real signal. Then a written check: what production code went to the vendor, under what terms. It becomes a case study for the org, not a quiet exception.",
            "My rule for every engineering leader: no AI tool touches production code until it has passed our eval harness on our codebase and the data-processing terms are signed off by security - both, in writing, before rollout.",
            "I'd set the evaluation cadence up front next time - we lost two weeks because each lead was benchmarking a different thing.",
        ],
    },
    "go_to_market": {
        "ic": [
            "Growth marketing manager for the savings product. ChatGPT daily for campaign copy variants and subject-line testing, Jasper for landing pages, and a Claude project loaded with our brand voice guide. I don't use AI for pricing claims or rate numbers - those come only from the approved rate sheet.",
            "I'd start from the approved claims doc, paste the product one-pager and brand voice guide into the prompt, and instruct: use only claims from this document, mark anything you add as UNVERIFIED. Then I iterate - first draft is always too salesy, so I tighten tone against the guide.",
            "Every number and product claim gets checked against the approved claims sheet before anyone else sees it - AI once drafted 'up to 4.5% returns' when our approved figure was different, and that would have been a compliance incident. My bar is: legal could read any line cold and find nothing to flag.",
            "Pull the draft from the review queue right away and flag the claim to legal and the PM - that number was never approved for public use. Then I'd add it to our blocked-claims list so the next draft can't reuse it silently.",
            "One rule: no AI-drafted copy goes live until someone who owns the claims sheet has initialed every factual statement. We run that as a checklist in the launch ticket.",
            "Next time I'd load the compliance-approved claims into the prompt from the start instead of fixing them at review.",
        ],
        "executive": [
            "CMO. I use ChatGPT for board narrative drafts and market-scan summaries, and I read our team's AI usage report monthly - which campaigns used AI drafting and what the edit distance was. We keep crisis comms fully human; speed matters less than judgment there.",
            "I'd set the frame first: what claims are approved, who owns sign-off, and what stays human. The team drafts with AI freely inside that frame. For this launch I'd want the claims register locked before any copy work starts, so drafting speed doesn't outrun approval.",
            "Averages hide the risk - I'd ask which specific claims in the draft are not yet in the approved register, and who checked. Our standing check is a claims diff: anything in copy that isn't in the register gets flagged automatically before it reaches brand review.",
            "Stop the send, obviously, but the interesting question is process: an unapproved number got within one click of going out, so the register check failed somewhere. I'd trace where, fix that gate, and tell legal the same day - they hear it from me, not from a complaint.",
            "My rule for every marketing lead: AI can draft anything, but no claim leaves the building unless it exists in the approved claims register with a named owner. One register, no exceptions per channel.",
            "I'd invest earlier in the claims register itself - most of our AI risk turned out to be an approvals problem, not a model problem.",
        ],
    },
    "care_operations": {
        "ic": [
            "Team lead on the VIP support queue, twelve agents. We use the helpdesk's AI draft-reply feature on most tickets, ChatGPT for summarizing long escalation threads, and I keep a prompt library for common refund scenarios. We don't let AI draft anything on legal-threat tickets - those go straight to a human senior.",
            "Read the customer thread first, then check the draft against the refund policy table before anything else - tone second, facts first. When I prompt for a redraft I paste the actual policy paragraph and the customer's last two messages, and tell it: offer only what this policy allows, keep the apology, drop the promises.",
            "The exact failure mode we've seen: drafts that sound perfect and overpromise. I caught one offering a full-year refund when policy caps at ninety days. So every draft gets a policy check against the table - amount, eligibility window, exception authority - before send. My bar: nothing reaches a customer that I couldn't defend to the policy owner line by line.",
            "Stop that send immediately - the draft exceeds policy. I'd rewrite the offer to what policy actually allows, and if the agent believes an exception is right, that goes to the exceptions queue where ops managers decide, not into a one-click send. Then I'd log it - we track how often AI drafts overpromise, it feeds our prompt fixes.",
            "One rule for agents: an AI draft is a starting point, and any draft with a number in it - refund, credit, timeline - gets checked against the policy table before send. That's on a laminated card on every desk, literally.",
            "I'd push for the policy table to be embedded in the AI tool itself so drafts start from policy instead of being corrected back to it.",
        ],
        "executive": [
            "VP of customer operations - about four hundred agents across three product lines. I use ChatGPT for ops reviews and workforce-planning scenarios, and I get a weekly digest of our AI-assist pilot metrics. We kept AI out of complaints-to-regulators entirely; that queue stays human end to end.",
            "Before any rollout decision I'd want the pilot instrumented per queue, not on averages: handling time, escalation rate, reopen rate, and customer-effort score, each by queue and ticket type. Plus a named owner per queue who reviews a sample of AI-assisted replies weekly.",
            "Mixed pilot data is exactly why you go queue by queue. Handling time down in one queue is real value, but escalations quietly rising elsewhere means the assist is mishandling a ticket type - I'd want the escalation transcripts sampled and read before expanding anything.",
            "The complaint surfacing it is the failure: the rollout ran without a per-queue rollback trigger. I'd pause expansion, keep the healthy queue live, have the queue lead pull fifty escalated tickets to find what the tool gets wrong, and set an explicit metric threshold that auto-pauses the assist next time - nobody should discover this from a customer.",
            "My rule for every queue lead: before your queue goes live, you sign off on the rollback trigger - the metric and the threshold that turns the tool off - and you own watching it weekly. If you can't name the trigger, you're not ready to turn it on.",
            "I'd stage the rollout by ticket type rather than by queue next time - the failure pattern followed ticket complexity, not team.",
        ],
    },
}

WEAK_ANSWERS: Dict[str, List[str]] = {
    # Engaged enough to pass the effort gate (not one-word), but no concrete tools-to-task
    # mapping, no prompting craft, no verification story, no ownership, no bar, no risk floor.
    "product_engineering": [
        "I'm in the product team, I do specs and things like that for our features.",
        "I would probably just ask the AI to write the spec for me, it is usually pretty good at that stuff.",
        "I guess I would read it over quickly to see if it looks fine and then send it to the engineers.",
        "That is not really my problem to be honest, someone from security probably handles those things.",
        "Maybe just tell people to use it carefully and not do anything too crazy with it.",
        "Not much really, I think it went fine, AI is going to do most of this for us anyway soon.",
    ],
    "go_to_market": [
        "I work in marketing on campaigns and social media posts and that kind of thing.",
        "Honestly I would just tell ChatGPT to write the launch email, it writes better than most people.",
        "I would give it a quick read to make sure it sounds good and exciting and then schedule it.",
        "I mean the number is roughly true anyway so I do not think it is a big deal to keep it in.",
        "Maybe a rule like make sure the copy sounds on brand before you send it out.",
        "Nothing really comes to mind, the tools are getting better so it will sort itself out.",
    ],
    "care_operations": [
        "I work in customer support, answering tickets and helping customers with their problems.",
        "If the draft is already written I would probably just send it, the AI knows the policies better than me.",
        "It sounds nice and polite so I do not see why I would need to change anything about it.",
        "I would probably still send it, the customer is angry and a bigger refund would calm them down.",
        "Just be polite to customers and use common sense I guess, that usually works.",
        "Not really, I think AI replies are fine as they are, customers cannot even tell the difference.",
    ],
}

QUESTIONS = [
    "What is your role, and which AI tools do you actually use in a normal week?",
    "What would you do first to handle this?",
    "The draft looks solid at first glance - what would you check before anyone else sees it?",
    "Something just went wrong here - what do you do right now?",
    "What is one rule you would want everyone to follow before using AI for this?",
    "Looking back, what is one thing you would do differently next time?",
]


def build_transcript(answers: List[str]) -> List[dict]:
    msgs: List[dict] = []
    for q, a in zip(QUESTIONS, answers):
        msgs.append({"role": "model", "content": q})
        msgs.append({"role": "user", "content": a})
    return msgs


def _norm(s: str) -> str:
    t = re.sub(r"[‘’“”'\"]", "", (s or "").lower())
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def check_quotes_verbatim(scores: dict, msgs: List[dict]) -> List[str]:
    """Every returned evidence quote must exist (normalized) in the participant's own turns."""
    problems: List[str] = []
    user_text = _norm(" ".join(m["content"] for m in msgs if m["role"] == "user"))
    for i in range(1, 7):
        d = scores.get(f"D{i}") or {}
        for q in d.get("evidence_quotes") or []:
            if _norm(q) not in user_text:
                problems.append(f"D{i} quote not verbatim: {q[:80]!r}")
    return problems


def check_consistency(scores: dict, label: str) -> List[str]:
    problems: List[str] = []
    for i in range(1, 7):
        d = scores.get(f"D{i}") or {}
        quotes = d.get("evidence_quotes") or []
        score = float(d.get("score", 0) or 0)
        if not quotes and score > 3.0:
            problems.append(f"{label}: D{i}={score} with zero grounded quotes (cap failed)")
    return problems


def run_llm_validation(families: List[str]) -> bool:
    ok = True
    rows = []
    for fam in families:
        for level in ("ic", "executive"):
            ass = build_assessment_block(level, fam)
            var = {"assessment": ass, "scenario_plan": se.build_scenario_plan(ass, f"val-{fam}-{level}"), "version": 2}
            results = {}
            for kind in ("strong", "weak"):
                answers = STRONG_ANSWERS[fam][level] if kind == "strong" else WEAK_ANSWERS[fam]
                msgs = build_transcript(answers)
                evidence = se.extract_session_evidence(msgs, var)
                scores = gs.score_transcript(msgs, var, evidence=evidence)
                results[kind] = scores
                problems = check_quotes_verbatim(scores, msgs) + check_consistency(scores, f"{fam}/{level}/{kind}")
                for p in problems:
                    ok = False
                    print(f"  FAIL {p}")
                time.sleep(0.4)

            s, w = results["strong"], results["weak"]
            s_c, w_c = float(s.get("AiQ_0_100") or 0), float(w.get("AiQ_0_100") or 0)
            sep = s_c - w_c
            dims_s = [float((s.get(f"D{i}") or {}).get("score", 0) or 0) for i in range(1, 7)]
            dims_w = [float((w.get(f"D{i}") or {}).get("score", 0) or 0) for i in range(1, 7)]
            row = {
                "family": fam,
                "level": level,
                "strong_composite": s_c,
                "weak_composite": w_c,
                "separation": round(sep, 1),
                "strong_band": s.get("maturity_band"),
                "weak_band": w.get("maturity_band"),
                "strong_dims": dims_s,
                "weak_dims": dims_w,
            }
            rows.append(row)
            if sep < 15.0:
                ok = False
                print(f"  FAIL {fam}/{level}: separation {sep:.1f} < 15 (strong {s_c}, weak {w_c})")
            # Weak transcripts contain no real risk behavior -> D6 must not read high.
            if dims_w[5] > 4.0:
                ok = False
                print(f"  FAIL {fam}/{level}: weak D6={dims_w[5]} despite no risk content")
            # Bands are derived from the composite in code (SRS boundaries) — verify they track it.
            for kind, sc, comp in (("strong", s, s_c), ("weak", w, w_c)):
                want_band = gs._band_for_composite(comp)
                if sc.get("maturity_band") != want_band:
                    ok = False
                    print(
                        f"  FAIL {fam}/{level}/{kind}: band {sc.get('maturity_band')} "
                        f"does not match composite {comp} (expected {want_band})"
                    )

    print("\n=== SEPARATION TABLE ===")
    print(f"{'family':<22}{'level':<12}{'strong':>8}{'weak':>8}{'sep':>7}  bands")
    for r in rows:
        print(
            f"{r['family']:<22}{r['level']:<12}{r['strong_composite']:>8}{r['weak_composite']:>8}"
            f"{r['separation']:>7}  {r['strong_band']} vs {r['weak_band']}"
        )
    out_path = ROOT / "scripts" / "last_scoring_validation.json"
    out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nFull results: {out_path}")
    return ok


def run_cluster_matrix_check() -> bool:
    ok = True
    print("=== PILOT MATRIX: scenario cluster per level x family ===")
    for fam in PILOT_FAMILIES:
        for level in PILOT_LEVELS:
            got = se._scenario_cluster(fam, level)
            want = EXPECTED_CLUSTERS[(fam, level)]
            mark = "ok " if got == want else "FAIL"
            if got != want:
                ok = False
            ass = build_assessment_block(level, fam)
            plan = se.build_scenario_plan(ass, "matrix-check")
            title = (plan.get("primary") or {}).get("title", "?")
            print(f"  {mark} {fam:<22} {level:<15} -> {got:<14} ({title})")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", default=",".join(PILOT_FAMILIES))
    ap.add_argument("--skip-llm", action="store_true", help="Cluster matrix check only")
    args = ap.parse_args()

    ok = run_cluster_matrix_check()

    if not args.skip_llm:
        mode, err = llm_mode()
        if mode == "error":
            print(f"\nNo LLM backend ({err}) — skipping scoring validation.")
            sys.exit(2)
        print(f"\nLLM backend: {mode}\n=== SCORING VALIDATION (strong vs weak) ===")
        families = [f.strip() for f in args.families.split(",") if f.strip()]
        ok = run_llm_validation(families) and ok

    print("\n=== VALIDATION:", "PASS" if ok else "FAIL", "===")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
