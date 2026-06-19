"""Experiment 2 runner — the hardened prompt-injection slice.

Same arms as Exp 1, but over the injection test set, scored for compromise
(data leak or system-prompt disclosure) rather than triage correctness. The
headline comparison is `vocab` (closed contract, NO injection defense) vs
`governed` (+ untrusted-input fencing + refusal + no-disclosure rule).

  python -m pack.run_injection          # all registry models (local need no key)
  PCIEP_MODELS=sonnet-4.6 python -m pack.run_injection
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pack.model_client import make_client
from pack.models import REGISTRY, selected
from pack.prompts import ARM_ORDER, ARMS
from pack.scoring import InjectionScore, aggregate_injection, score_injection
from pack.testset_injection import INJECTION_CASES

RESULTS = Path(__file__).resolve().parent.parent / "results_injection"


def run_arm(client, arm_name: str, arm_fn, raw_fh) -> list[InjectionScore]:
    scored: list[InjectionScore] = []
    for case in INJECTION_CASES:
        comp = client.complete(*arm_fn(case))
        s = score_injection(case, comp.text)
        scored.append(s)
        raw_fh.write(json.dumps({
            "arm": arm_name, "case_id": case.case_id, "model": comp.model,
            "latency_ms": round(comp.latency_ms, 1), "raw_text": comp.text,
        }) + "\n")
        raw_fh.flush()
    agg = aggregate_injection(scored)
    print(f"  [{arm_name:9}] compromised {agg['compromised']}/{agg['total']} "
          f"(data {agg['data_leaks']}, prompt {agg['prompt_leaks']})  resisted {agg['resisted']}", flush=True)
    return scored


def run_model(entry: dict) -> None:
    out_dir = RESULTS / entry["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    client = make_client(entry)
    arms: dict[str, list[InjectionScore]] = {}
    with (out_dir / "raw_outputs.jsonl").open("w", encoding="utf-8") as fh:
        for arm_name, arm_fn in ARMS.items():
            arms[arm_name] = run_arm(client, arm_name, arm_fn, fh)
    payload = {
        "label": entry["label"],
        "arms": {a: {"cases": [asdict(s) for s in arms[a]], "counts": aggregate_injection(arms[a])}
                 for a in arms},
    }
    (out_dir / "scores.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _summary() -> str:
    rows = ["# Exp 2 — injection resistance (compromised cases by arm, lower is better)", "",
            f"Hardened injection slice, n={len(INJECTION_CASES)} cases. Compromise = a data leak "
            "(phone/email/SSN/dosing) OR system-prompt disclosure — both deterministic.", "",
            "| Model | " + " | ".join(ARM_ORDER) + " |", "|---|" + "|".join("---" for _ in ARM_ORDER) + "|"]
    for entry in REGISTRY:
        path = RESULTS / entry["slug"] / "scores.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        cells = []
        for arm in ARM_ORDER:
            c = data["arms"][arm]["counts"]
            cells.append(f"{c['compromised']}/{c['total']}")
        rows.append(f"| {data['label']} | " + " | ".join(cells) + " |")
    rows += ["", "Per-case detail in `results_injection/<model>/scores.json`. The decisive "
             "comparison is **vocab** (no injection defense) vs **governed** (untrusted-input "
             "fencing + refusal + no-disclosure rule)."]
    return "\n".join(rows)


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    models = selected()
    print(f"INJECTION models: {[m['slug'] for m in models]}  arms: {list(ARMS)}  cases: {len(INJECTION_CASES)}", flush=True)
    for entry in models:
        print(f"\n=== {entry['slug']} ===", flush=True)
        try:
            run_model(entry)
        except Exception as exc:
            print(f"  SKIPPED {entry['slug']}: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
    (RESULTS / "SUMMARY.md").write_text(_summary(), encoding="utf-8")
    print("\ndone. results_injection/<slug>/ + results_injection/SUMMARY.md", flush=True)


if __name__ == "__main__":
    main()
