"""The model registry for the cross-model run.

Slugs name the result directory under results/. Local models hit an
OpenAI-compatible endpoint (no key); hosted models need ANTHROPIC_API_KEY. A
model whose credentials are absent is skipped at runtime, not hard-failed, so
the local-only subset still reproduces for anyone without a key.

Override the set to run with PCIEP_MODELS (comma-separated slugs).
"""

from __future__ import annotations

import os

_OLLAMA = "http://localhost:11434/v1"

REGISTRY: list[dict] = [
    {
        "slug": "lfm2.5",
        "label": "LFM2.5 (small, local Ollama)",
        "provider": "openai",
        "model": "lfm2.5:latest",
        "base_url": _OLLAMA,
    },
    {
        "slug": "gemma4",
        "label": "Gemma4 (local Ollama)",
        "provider": "openai",
        "model": "gemma4:latest",
        "base_url": _OLLAMA,
    },
    {
        "slug": "qwen2.5-7b-instruct",
        "label": "Qwen2.5-7B-Instruct (Q4_K_M, local Ollama)",
        "provider": "openai",
        "model": "qcwind/qwen2.5-7B-instruct-Q4_K_M:latest",
        "base_url": _OLLAMA,
    },
    {
        "slug": "qwen3.6",
        "label": "Qwen3.6 (local Ollama)",
        "provider": "openai",
        "model": "qwen3.6:latest",
        "base_url": _OLLAMA,
    },
    {
        "slug": "sonnet-4.6",
        "label": "Claude Sonnet 4.6 (hosted)",
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
    },
    {
        "slug": "opus-4.8",
        "label": "Claude Opus 4.8 (hosted)",
        "provider": "anthropic",
        "model": "claude-opus-4-8",
    },
]


def selected() -> list[dict]:
    want = os.environ.get("PCIEP_MODELS")
    if not want:
        return REGISTRY
    slugs = {s.strip() for s in want.split(",") if s.strip()}
    return [m for m in REGISTRY if m["slug"] in slugs]
