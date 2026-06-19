# Cross-model summary — governed prompt vs baseline

Governed-action validity (↑) and critical-safety-failure rate (↓), baseline vs full governed arm, per model. n=24 synthetic cases each.

| Model | Baseline valid | Governed valid | Δ valid | Baseline crit | Governed crit | Adopted |
|---|---|---|---|---|---|---|
| LFM2.5 (small, local Ollama) | 0% | 83% | +83pp | 38% | 0% | yes |
| Gemma4 (local Ollama) | 0% | 62% | +62pp | 33% | 29% | no |
| Qwen2.5-7B-Instruct (Q4_K_M, local Ollama) | 0% | 75% | +75pp | 33% | 0% | yes |
| Qwen3.6 (local Ollama) | 0% | 79% | +79pp | 33% | 0% | yes |
| Claude Sonnet 4.6 (hosted) | 0% | 96% | +96pp | 33% | 0% | yes |
| Claude Opus 4.8 (hosted) | 0% | 88% | +88pp | 33% | 0% | yes |

Per-model ablation tables and claim ledgers are in `results/<model>/claim_ledger.md`.
