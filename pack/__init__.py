"""Prompt-optimization evidence pack — patient-communication triage agent.

A standalone, reproducible experiment that measures the effect of one isolated
variable — the prompt architecture — on the safety and reliability of an LLM
triage agent. The model boundary is a thin OpenAI-compatible adapter so the
study runs credential-free against a local self-hosted model, or against hosted
Claude with a key. Design lineage: the Private Context Inference Gateway
(self-hosted vs hosted routing); this pack is intentionally self-contained.
"""
