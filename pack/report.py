"""Turn scored arms into per-model metrics, a pre-registered verdict, an ablation
table, a per-model ClaimLedger, and a cross-model summary.

Everything is derived from the scored results and the locked thresholds in
prereg/replacement_rule.yaml — nothing hand-entered, so claims can't drift from
the numbers and the verdict can't be reverse-fit.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from pack.prompts import ARM_ORDER, PRIMARY_ARM
from pack.scoring import CaseScore, aggregate

PREREG = Path(__file__).resolve().parent.parent / "prereg"

# Metrics shown in the ablation table, with display label and arrow direction.
_SHOWN = [
    ("governed_action_valid_rate", "Governed-action validity ↑"),
    ("schema_failure_rate", "Schema non-compliance ↓"),
    ("critical_safety_failure_rate", "Critical safety failures ↓"),
    ("red_flag_miss_rate", "Red-flag emergencies missed ↓"),
    ("over_escalation_rate", "Over-escalation ↓"),
]


def _rate(num: int, den: int) -> float:
    return round(num / den, 4) if den else 0.0


def _pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def arm_rates(scores: list[CaseScore]) -> dict:
    a = aggregate(scores)
    return {
        "schema_failure_rate": _rate(a["schema_failures"], a["total"]),
        "governed_action_valid_rate": _rate(a["governed_valid"], a["total"]),
        "critical_safety_failure_rate": _rate(a["critical_safety_failures"], a["total"]),
        "red_flag_miss_rate": _rate(a["red_flag_missed"], a["red_flag_total"]),
        "under_escalation_rate": _rate(a["under_escalations"], a["total"]),
        "over_escalation_rate": _rate(a["over_escalations"], a["total"]),
        "leak_rate": _rate(a["leaks"], a["total"]),
        "_counts": a,
    }


def build_metrics(all_scores: dict[str, list[CaseScore]], model_name: str, label: str = "") -> dict:
    arms = {arm: arm_rates(all_scores[arm]) for arm in ARM_ORDER if arm in all_scores}
    base = arms["baseline"]
    deltas = {
        arm: {k: round(arms[arm][k] - base[k], 4) for k in base if k != "_counts"}
        for arm in arms
    }
    return {"model": model_name, "label": label or model_name, "arms": arms, "deltas_vs_baseline": deltas}


def _rule() -> dict:
    return yaml.safe_load((PREREG / "replacement_rule.yaml").read_text())["adopt_improved_if"]


def verdict(metrics: dict) -> dict:
    rule = _rule()
    base, prim = metrics["arms"]["baseline"], metrics["arms"][PRIMARY_ARM]
    primary_delta = round(prim["governed_action_valid_rate"] - base["governed_action_valid_rate"], 4)
    over_reg = round(prim["over_escalation_rate"] - base["over_escalation_rate"], 4)
    checks = {
        f"primary_metric_delta >= {rule['primary_metric_delta_min']:.2f}":
            (primary_delta, primary_delta >= rule["primary_metric_delta_min"]),
        f"safety_ceiling <= {rule['safety_ceiling_max']:.2f}":
            (prim["critical_safety_failure_rate"], prim["critical_safety_failure_rate"] <= rule["safety_ceiling_max"]),
        f"over_escalation_regression <= {rule['over_escalation_regression_max']:.2f}":
            (over_reg, over_reg <= rule["over_escalation_regression_max"]),
    }
    return {"adopted": all(p for _, p in checks.values()), "checks": checks}


def _ablation_table(metrics: dict) -> list[str]:
    arms = [a for a in ARM_ORDER if a in metrics["arms"]]
    header = "| Metric | " + " | ".join(arms) + " |"
    sep = "|---|" + "|".join("---" for _ in arms) + "|"
    rows = [header, sep]
    for key, label in _SHOWN:
        cells = " | ".join(_pct(metrics["arms"][a][key]) for a in arms)
        rows.append(f"| {label} | {cells} |")
    return rows


def _residual_lines(metrics: dict) -> list[str]:
    prim = metrics["arms"][PRIMARY_ARM]
    c = prim["_counts"]
    lines = [
        f"- The full governed arm is **{_pct(prim['governed_action_valid_rate'])} governed-valid, "
        f"not 100%**: {c['schema_failures']} residual schema failures, {c['under_escalations']} "
        f"under-escalations on ambiguous non-red-flag cases, {c['action_inappropriate']} "
        "valid-but-off-gold action choices.",
    ]
    if prim["critical_safety_failure_rate"] == 0:
        lines.append(
            f"- **0 critical safety failures and 0/{c['red_flag_total']} red-flag emergencies missed "
            "— on these 24 synthetic cases only.** Small n bounds the true rate loosely; this is NOT "
            "a demonstration of zero failures. Keep human oversight.")
    else:
        lines.append(
            f"- Full governed arm still has **{_pct(prim['critical_safety_failure_rate'])} critical "
            f"safety failures** ({_pct(prim['red_flag_miss_rate'])} red-flag misses) — not zero.")
    return lines


def ledger_markdown(metrics: dict, verd: dict) -> str:
    out = [
        f"# ClaimLedger — {metrics['label']}",
        "",
        "Generated from scored results against the pre-registered thresholds in "
        "`prereg/replacement_rule.yaml`. Not hand-edited.",
        "",
        "## Ablation (deterministic metrics, n=24 synthetic cases)",
        "Each arm adds one control to the previous: baseline → +closed vocab/schema → "
        "+red-flag rule → +authority/refusal (full governed).",
        *_ablation_table(metrics),
        "",
        f"## Pre-registered verdict (baseline → {PRIMARY_ARM})",
        f"**Adopted: {verd['adopted']}** (all locked thresholds must pass)",
        "",
        "| Threshold | Observed | Pass |",
        "|---|---|---|",
    ]
    for name, (value, passed) in verd["checks"].items():
        out.append(f"| {name} | {value:+.2f} | {'PASS' if passed else 'FAIL'} |")
    out += ["", "## Residuals (stated, not hidden)", *_residual_lines(metrics), ""]
    return "\n".join(out)


def summarize(entries: list[dict]) -> str:
    """entries: list of {metrics, verdict}. Cross-model headline table."""
    out = [
        "# Cross-model summary — governed prompt vs baseline",
        "",
        "Governed-action validity (↑) and critical-safety-failure rate (↓), baseline vs full "
        "governed arm, per model. n=24 synthetic cases each.",
        "",
        "| Model | Baseline valid | Governed valid | Δ valid | Baseline crit | Governed crit | Adopted |",
        "|---|---|---|---|---|---|---|",
    ]
    for e in entries:
        m, v = e["metrics"], e["verdict"]
        b, g = m["arms"]["baseline"], m["arms"][PRIMARY_ARM]
        dv = (g["governed_action_valid_rate"] - b["governed_action_valid_rate"]) * 100
        out.append(
            f"| {m['label']} | {_pct(b['governed_action_valid_rate'])} | "
            f"{_pct(g['governed_action_valid_rate'])} | {dv:+.0f}pp | "
            f"{_pct(b['critical_safety_failure_rate'])} | {_pct(g['critical_safety_failure_rate'])} | "
            f"{'yes' if v['adopted'] else 'no'} |")
    out += [
        "",
        "Per-model ablation tables and claim ledgers are in `results/<model>/claim_ledger.md`.",
        "",
    ]
    return "\n".join(out)
