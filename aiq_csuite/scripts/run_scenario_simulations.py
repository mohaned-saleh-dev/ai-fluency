#!/usr/bin/env python3
"""
Run N end-to-end scenario-stack interview simulations and print aggregate findings.
Usage: cd aiq_csuite && python3 scripts/run_scenario_simulations.py [--n 12] [--dry]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gemini_service as gs
import scenario_engine as se
from assessment_profiles import build_assessment_block
from llm_json import llm_mode

_SOFT = re.compile(
    r"^\s*(that[’']?s|it sounds like|understood|great\b|nice\b|i appreciate|thanks for sharing|makes sense)",
    re.I,
)
_SCENARIO_MARK = re.compile(r"picture this", re.I)
_TWIST_MARK = re.compile(r"something goes wrong", re.I)
_LABEL_LEAK = re.compile(r"\*\*(scenario\s*[—–-]|twist|stepping back|one last reflection)", re.I)
_DIM_BANNER = re.compile(r"\[Dim:\s*D[1-6]", re.I)
_IN_SCENARIO_LOOP = re.compile(
    r"\b(in the scenario where you|when evaluating the model-written|"
    r"automation (versus|vs\.?) forecasting|supporting automation)\b",
    re.I,
)
_GENERIC = re.compile(
    r"how do you see|changing the way your team|specific outcomes or efficiencies|"
    r"approach training or onboarding|skill alignment|leveraging AI to enhance",
    re.I,
)


@dataclass
class TurnRecord:
    turn: int
    phase: str
    user: str
    assistant: str
    phase_shift: Optional[str]
    flags: Dict[str, bool] = field(default_factory=dict)


@dataclass
class SimResult:
    sim_id: str
    profile: str
    persona: str
    scenario_title: str
    turns: List[TurnRecord] = field(default_factory=list)
    phases_seen: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    used_llm: bool = True


PERSONAS: Dict[str, List[str]] = {
    "strong_exec": [
        "Head of strategy and ops building the COO office. ChatGPT, Copilot, and our internal copilot for decks, workflow diagrams, and first-pass memos.",
        "I'd paste anonymized requirements and API constraints, tell the model role=staff engineer reviewer, forbid inventing policy. Second human reads before eng sees it.",
        "Kill the thread, ping security, pull retention settings, send a one-pager on what never goes in shared GPT.",
        "COO and I sign external specs; team leads run a 5-point checklist on any AI draft that leaves the function.",
    ],
    "terse": [
        "COO office, strategy and ops. ChatGPT mostly.",
        "I'd use it for the spec I guess.",
        "Nothing specific.",
        "Tell the team to be careful.",
    ],
    "ic_product": [
        "Senior PM on payments. Cursor, ChatGPT, Figma AI for specs and user stories.",
        "Prompt: here's the retry API doc, output acceptance criteria only, do not invent fee amounts. I diff against the doc.",
        "Someone pasted customer IDs — revoke access, open incident, move to approved enterprise tenant.",
        "PMs can't ship AI specs without eng lead + compliance tag in Jira.",
    ],
    "vague_enthusiast": [
        "I lead GTM! We use ALL the AI tools — so much faster, game changer for the team.",
        "I'd definitely use AI to write everything, it's amazing.",
        "We just move fast and trust the tools.",
        "Everyone should use AI more!",
    ],
    "risk_focused": [
        "Compliance counsel. Copilot for internal drafts only on approved tenant.",
        "Brief: cite only attached policy PDF, escalate if answer touches licensing. No external paste.",
        "Model draft said 24h deletion — false for our vendor. Correct before legal sends.",
        "Front line gets a one-page allowed/not allowed list; anything else to counsel.",
    ],
    "asks_clarify": [
        "Head of ops. We use ChatGPT and Copilot for memos and planning.",
        "What do you mean?",
        "Oh, got it. I'd ask it to draft the memo from last quarter's deck, then check the numbers myself.",
        "I'd tell people not to paste customer data into it.",
        "Have the team lead read it before it goes to the COO.",
    ],
}

PROFILES = [
    ("head_of", "general_management", "strong_exec"),
    ("head_of", "general_management", "terse"),
    ("executive", "general_management", "vague_enthusiast"),
    ("head_of", "product_engineering", "ic_product"),
    ("people_manager", "go_to_market", "strong_exec"),
    ("head_of", "care_operations", "terse"),
    ("executive", "finance", "risk_focused"),
    ("head_of", "risk_legal", "risk_focused"),
    ("ic", "product_engineering", "ic_product"),
    ("people_manager", "hr_people", "terse"),
    ("head_of", "go_to_market", "vague_enthusiast"),
    ("head_of", "general_management", "asks_clarify"),
]


def _analyze_reply(text: str) -> Dict[str, bool]:
    return {
        "soft_opener": bool(_SOFT.search(text or "")),
        "has_scenario_brief": bool(_SCENARIO_MARK.search(text or "")),
        "has_twist": bool(_TWIST_MARK.search(text or "")),
        "dim_banner": bool(_DIM_BANNER.search(text or "")),
        "generic_wording": bool(_GENERIC.search(text or "")),
        "label_leak": bool(_LABEL_LEAK.search(text or "")),
        "has_question": "?" in (text or ""),
    }


def run_one_sim(
    sim_id: str,
    level: str,
    job_family: str,
    persona_key: str,
    dry: bool,
) -> SimResult:
    ass = build_assessment_block(level, job_family)
    var = gs.build_variation_for_session(f"sim-{sim_id}", ass)
    var["assessment"] = ass
    plan = var.get("scenario_plan") or {}
    title = (plan.get("primary") or {}).get("title", "?")
    profile_lbl = f"{ass.get('level_label')} / {ass.get('job_family_label')}"
    res = SimResult(
        sim_id=sim_id,
        profile=profile_lbl,
        persona=persona_key,
        scenario_title=title,
        used_llm=not dry,
    )
    messages: List[dict] = []
    phase_history: List[str] = ["anchor"]
    user_lines = PERSONAS.get(persona_key, PERSONAS["terse"])

    # Opening
    opening = gs.opening_message(var)
    messages.append({"role": "model", "content": opening})
    res.turns.append(
        TurnRecord(0, "anchor", "", opening, None, _analyze_reply(opening))
    )

    max_user_turns = min(se.MAX_USER_TURNS + 1, len(user_lines) + 2)
    for ui in range(max_user_turns):
        user_text = user_lines[ui] if ui < len(user_lines) else "That's all from my side."
        flow = se.compute_flow_state(
            messages, phase_history, last_user_message=user_text
        )
        phase = flow.get("current_phase") or "anchor"

        if dry:
            turn = {
                "reply": se._fallback_question(
                    flow.get("next_phase") if flow.get("must_advance_phase") else phase,
                    plan,
                    user_text,
                ),
                "phase_shift": (
                    {"phase": flow["next_phase"], "label": dict(se.PHASES).get(flow["next_phase"], "")}
                    if flow.get("must_advance_phase") and flow.get("next_phase")
                    else None
                ),
                "session_suggests_complete": phase == "close",
                "planner_meta": {"phase": phase},
            }
            if turn.get("phase_shift"):
                brief = se._scenario_brief_for(turn["phase_shift"]["phase"], plan)
                if brief:
                    turn["reply"] = f"{brief}\n\n{turn['reply']}"
        else:
            try:
                turn = se.plan_and_render_turn(
                    flow, var, messages, user_text, "No special flag on this turn."
                )
            except Exception as e:
                res.errors.append(f"turn {ui+1}: {e!s}")
                break

        reply = (turn.get("reply") or "").strip()
        ps = turn.get("phase_shift")
        if ps and ps.get("phase"):
            phase_history.append(ps["phase"])
            if ps["phase"] not in res.phases_seen:
                res.phases_seen.append(ps["phase"])

        meta_phase = (turn.get("planner_meta") or {}).get("phase") or phase
        flags = _analyze_reply(reply)
        res.turns.append(
            TurnRecord(ui + 1, meta_phase, user_text[:120], reply[:500], ps.get("phase") if ps else None, flags)
        )
        messages.append({"role": "user", "content": user_text})
        messages.append({"role": "model", "content": reply})

        if turn.get("session_suggests_complete"):
            break
        if meta_phase == "close" and ui >= 4:
            break

    return res


def regression_gates(agg: Dict[str, Any], results: List[SimResult]) -> List[str]:
    """Fail CI if scenario-stack quality regresses."""
    fails: List[str] = []
    n = agg.get("n") or 0
    if n and str(agg.get("scenario_shown_rate", "")).split("/")[0] != str(n):
        fails.append(f"scenario not shown in all sims: {agg.get('scenario_shown_rate')}")
    if int(agg.get("soft_opener_turns") or 0) > 0:
        fails.append(f"soft openers: {agg.get('soft_opener_turns')}")
    if int(agg.get("label_leak_turns") or 0) > 0:
        fails.append(f"internal labels leaked to user: {agg.get('label_leak_turns')}")
    for r in results:
        if r.persona != "asks_clarify":
            continue
        clar = next((t for t in r.turns if t.user.strip().lower() == "what do you mean?"), None)
        if clar is None:
            continue
        if clar.phase_shift is not None:
            fails.append(f"sim {r.sim_id}: clarification advanced the phase ({clar.phase_shift})")
    if int(agg.get("in_scenario_loop_turns") or 0) > n:
        fails.append(f"too many 'In the scenario where' loops: {agg.get('in_scenario_loop_turns')}")
    reached_close = str(agg.get("reached_close", "0/0"))
    if n and not reached_close.startswith(str(n)):
        fails.append(f"close phase not reached: {reached_close}")
    for r in results:
        if r.persona == "terse" and "general" in r.profile.lower():
            thin_turns = [t for t in r.turns if "nothing specific" in t.user.lower()]
            for tt in thin_turns:
                nxt = next((x for x in r.turns if x.turn == tt.turn + 1), None)
                if nxt and _IN_SCENARIO_LOOP.search(nxt.assistant or ""):
                    fails.append(f"sim {r.sim_id}: thin answer still got portfolio loop")
    return fails


def aggregate(results: List[SimResult]) -> Dict[str, Any]:
    n = len(results)
    scenario_turn_idxs = []
    twist_count = 0
    soft_count = 0
    generic_count = 0
    loop_stem_count = 0
    dim_banner_count = 0
    label_leak_count = 0
    reached_primary = 0
    reached_complication = 0
    reached_close = 0
    avg_model_turns = 0
    errors = 0

    for r in results:
        if r.errors:
            errors += 1
        for i, t in enumerate(r.turns):
            if t.flags.get("has_scenario_brief"):
                scenario_turn_idxs.append((r.sim_id, i))
            if t.flags.get("has_twist"):
                twist_count += 1
            if t.flags.get("soft_opener"):
                soft_count += 1
            if t.flags.get("generic_wording"):
                generic_count += 1
            if _IN_SCENARIO_LOOP.search(t.assistant or ""):
                loop_stem_count += 1
            if t.flags.get("dim_banner"):
                dim_banner_count += 1
            if t.flags.get("label_leak"):
                label_leak_count += 1
        if "primary" in r.phases_seen or any(t.flags.get("has_scenario_brief") for t in r.turns):
            reached_primary += 1
        if "complication" in r.phases_seen or any(t.flags.get("has_twist") for t in r.turns):
            reached_complication += 1
        if any(t.phase == "close" for t in r.turns) or "close" in r.phases_seen:
            reached_close += 1
        avg_model_turns += len([t for t in r.turns if t.turn >= 0])

    return {
        "n": n,
        "scenario_shown_rate": f"{reached_primary}/{n}",
        "twist_shown_rate": f"{twist_count}/{n} sims with twist marker",
        "soft_opener_turns": soft_count,
        "generic_wording_turns": generic_count,
        "in_scenario_loop_turns": loop_stem_count,
        "dim_banner_turns": dim_banner_count,
        "label_leak_turns": label_leak_count,
        "reached_complication": f"{reached_complication}/{n}",
        "reached_close": f"{reached_close}/{n}",
        "avg_model_turns": round(avg_model_turns / max(1, n), 1),
        "sim_errors": errors,
        "scenario_at_turn": scenario_turn_idxs[:5],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--dry", action="store_true", help="Fallback questions only (no API)")
    args = ap.parse_args()

    mode, err = llm_mode()
    if args.dry:
        print("DRY RUN (fallback questions only)\n")
    elif mode == "error":
        print(f"No LLM backend: {err}\nRunning DRY fallback sims instead.\n")
        args.dry = True
    else:
        print(f"LLM backend: {mode}\n")

    n = min(args.n, len(PROFILES))
    results: List[SimResult] = []
    t0 = time.time()
    for i in range(n):
        level, fam, persona = PROFILES[i]
        sid = f"{i+1:02d}"
        print(f"Sim {sid} — {level}/{fam} persona={persona} …", flush=True)
        results.append(run_one_sim(sid, level, fam, persona, dry=args.dry))
        time.sleep(0.3 if not args.dry else 0)

    agg = aggregate(results)
    print(f"\nDone in {time.time()-t0:.1f}s\n")
    print("=== AGGREGATE ===")
    print(json.dumps(agg, indent=2))

    print("\n=== PER-SIM SUMMARY ===")
    for r in results:
        st = next((t.turn for t in r.turns if t.flags.get("has_scenario_brief")), "never")
        print(
            f"  {r.sim_id} {r.profile[:40]:40} | persona={r.persona:14} | "
            f"scenario@{st} | phases={','.join(r.phases_seen) or 'none'} | "
            f"title={r.scenario_title[:35]}"
        )
        if r.errors:
            print(f"      ERR: {r.errors}")

    print("\n=== SAMPLE: terse COO (sim 02) last 3 assistant lines ===")
    terse = next((r for r in results if r.persona == "terse" and "general" in r.profile.lower()), results[1] if len(results) > 1 else None)
    if terse:
        for t in terse.turns[-3:]:
            print(f"  [phase={t.phase}] {t.assistant[:220]}…")

    out_path = ROOT / "scripts" / "last_simulation_results.json"
    payload = {
        "aggregate": agg,
        "dry": args.dry,
        "sims": [
            {
                "id": r.sim_id,
                "profile": r.profile,
                "persona": r.persona,
                "scenario_title": r.scenario_title,
                "phases_seen": r.phases_seen,
                "errors": r.errors,
                "turns": [
                    {
                        "turn": t.turn,
                        "phase": t.phase,
                        "user": t.user,
                        "assistant": t.assistant,
                        "phase_shift": t.phase_shift,
                        "flags": t.flags,
                    }
                    for t in r.turns
                ],
            }
            for r in results
        ],
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nFull log: {out_path}")

    fails = regression_gates(agg, results)
    if fails:
        print("\n=== REGRESSION FAILURES ===")
        for f in fails:
            print("  -", f)
        if not args.dry:
            sys.exit(1)
    else:
        print("\n=== REGRESSION: PASS ===")


if __name__ == "__main__":
    main()
