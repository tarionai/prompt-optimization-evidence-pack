"""Run every ablation arm over the frozen test set, for each selected model.

The model is held constant within a run; only the prompt (arm) changes. Results
are written per model under results/<slug>/. A model whose credentials are
missing or whose endpoint is unreachable is skipped with a message, not a crash,
so the local-only subset still reproduces without a key.

  python -m pack.runner                      # all models in the registry
  PCIEP_MODELS=qwen2.5-7b-instruct python -m pack.runner   # a subset
Then aggregate:  python -m pack.summarize
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from pack.model_client import make_client
from pack.models import selected
from pack.prompts import ARMS
from pack.report import build_metrics, ledger_markdown, verdict
from pack.scoring import CaseScore, aggregate, score_case
from pack.testset import CASES

RESULTS = Path(__file__).resolve().parent.parent / "results"


def run_arm(client, arm_name: str, arm_fn, raw_fh) -> list[CaseScore]:
    scored: list[CaseScore] = []
    for case in CASES:
        system, user = arm_fn(case)
        completion = client.complete(system, user)
        score = score_case(case, completion.text)
        scored.append(score)
        raw_fh.write(json.dumps({
            "arm": arm_name, "case_id": case.case_id, "category": case.category,
            "model": completion.model, "latency_ms": round(completion.latency_ms, 1),
            "raw_text": completion.text,
        }) + "\n")
        raw_fh.flush()
    valid = sum(s.governed_action_valid for s in scored)
    crit = sum(s.critical_safety_failure for s in scored)
    print(f"  [{arm_name:9}] governed-valid {valid}/{len(scored)}  critical {crit}", flush=True)
    return scored


def run_model(entry: dict) -> dict[str, list[CaseScore]]:
    out_dir = RESULTS / entry["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    client = make_client(entry)
    all_scores: dict[str, list[CaseScore]] = {}
    with (out_dir / "raw_outputs.jsonl").open("w", encoding="utf-8") as fh:
        for arm_name, arm_fn in ARMS.items():
            all_scores[arm_name] = run_arm(client, arm_name, arm_fn, fh)

    scores_payload = {
        arm: {"cases": [asdict(s) for s in scores], "counts": aggregate(scores)}
        for arm, scores in all_scores.items()
    }
    (out_dir / "scores.json").write_text(json.dumps(scores_payload, indent=2), encoding="utf-8")
    metrics = build_metrics(all_scores, entry["model"], entry["label"])
    verd = verdict(metrics)
    (out_dir / "metrics.json").write_text(
        json.dumps({"metrics": metrics, "verdict": verd}, indent=2), encoding="utf-8")
    (out_dir / "claim_ledger.md").write_text(ledger_markdown(metrics, verd), encoding="utf-8")
    return all_scores


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    models = selected()
    print(f"models: {[m['slug'] for m in models]}  | arms: {list(ARMS)}  | cases: {len(CASES)}", flush=True)
    for entry in models:
        print(f"\n=== {entry['slug']} ({entry['model']}) ===", flush=True)
        try:
            run_model(entry)
        except Exception as exc:  # endpoint down / auth missing — skip, don't crash the run
            print(f"  SKIPPED {entry['slug']}: {type(exc).__name__}: {str(exc)[:160]}", flush=True)
    print("\ndone. per-model results in results/<slug>/. Run: python -m pack.summarize", flush=True)


if __name__ == "__main__":
    main()
