"""Aggregate per-model results into a single cross-model summary.

Reads every results/<slug>/metrics.json produced by the runner and writes
results/SUMMARY.md + results/summary.json. Order follows the registry so the
table reads small-local → frontier-hosted.

  python -m pack.summarize
"""

from __future__ import annotations

import json
from pathlib import Path

from pack.models import REGISTRY
from pack.report import summarize

RESULTS = Path(__file__).resolve().parent.parent / "results"


def main() -> None:
    entries = []
    for entry in REGISTRY:
        path = RESULTS / entry["slug"] / "metrics.json"
        if path.exists():
            entries.append(json.loads(path.read_text(encoding="utf-8")))
    if not entries:
        print("no per-model metrics found; run python -m pack.runner first")
        return
    (RESULTS / "SUMMARY.md").write_text(summarize(entries), encoding="utf-8")
    (RESULTS / "summary.json").write_text(
        json.dumps([e["metrics"] for e in entries], indent=2), encoding="utf-8")
    print(f"wrote results/SUMMARY.md over {len(entries)} model(s)")


if __name__ == "__main__":
    main()
