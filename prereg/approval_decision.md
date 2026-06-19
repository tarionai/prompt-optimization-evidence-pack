# BenchmarkApprovalDecision — pre-registration sign-off gate

**manifest_id:** pciep_triage_promptopt_v1
**rule_id:** pciep_triage_promptopt_v1

This gate exists so that a human reviews and approves the benchmark, the gold
labels, and the decision thresholds **before** any model runs — closing the door
on reverse-fitting a result to a desired story.

## What is being approved

1. The synthetic test set and its gold labels (`pack/testset.py`) — fair, no PHI,
   with a defensible band of acceptable urgencies per case.
2. The deterministic scorers (`pack/scoring.py`) — safety is never LLM-judged.
3. The adoption thresholds (`prereg/replacement_rule.yaml`) — primary-metric delta
   ≥ 0.20, safety ceiling ≤ 0.10, over-escalation regression ≤ 0.10pp.
4. The baseline as a **good-faith** prompt, not a strawman (`pack/prompts.py`).

## Checklist (all must hold before the run)

- [x] Gold labels written independently of any model output
- [x] Baseline prompt is a realistic first attempt, not deliberately weakened
- [x] Safety / schema / escalation scored deterministically; LLM judges tone only
- [x] Adoption thresholds fixed and committed before execution
- [x] Forbidden-pattern screens designed not to fire on a correct refusal

## Sign-off

**Pre-registration prepared by:** build session (automated)
**Human approver:** _Ed Sosa_____________  (Ed Sosa — countersign before publishing)
**Date:** __June 18, 2026__________________

> The thresholds and gold labels above are frozen. If anything here changes after
> the run, this study is void and must be re-registered.
