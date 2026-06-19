"""The model boundary — one uniform interface over self-hosted and hosted models.

Deliberately thin and self-contained so the published pack runs on its own. The
default target is a local OpenAI-compatible endpoint (Ollama / vLLM), which needs
no API key, so anyone can reproduce the run. A hosted Claude arm is available by
setting PCIEP_PROVIDER=anthropic with a key. The same prompt and the same scorers
apply to whichever model answers — only the model changes between arms is the
model; only the prompt changes within an arm.

Lineage: this mirrors the routing boundary of the Private Context Inference
Gateway; it is reimplemented small here rather than imported, to keep the artifact
standalone and verifiable.
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)
_UNCLOSED_THINK = re.compile(r"<think>.*\Z", re.DOTALL)


def strip_reasoning(text: str) -> str:
    """Reasoning models (deepseek-r1, qwen-r) emit <think>..</think> scratch.

    Remove complete blocks then any unterminated trailing block, so only the
    answer reaches the parser. The hidden reasoning is not part of the contract.
    """
    cleaned = _UNCLOSED_THINK.sub("", _THINK_BLOCK.sub("", text))
    return cleaned.strip()


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    base_url: str
    max_tokens: int
    timeout_s: float


def config_from_env() -> ModelConfig:
    return ModelConfig(
        provider=os.environ.get("PCIEP_PROVIDER", "openai"),
        model=os.environ.get("PCIEP_MODEL", "qwen2.5:7b-instruct"),
        base_url=os.environ.get("PCIEP_BASE_URL", "http://localhost:11434/v1"),
        max_tokens=int(os.environ.get("PCIEP_MAX_TOKENS", "1024")),
        timeout_s=float(os.environ.get("PCIEP_TIMEOUT", "240")),
    )


class OpenAICompatibleClient:
    """Any OpenAI-compatible server: local Ollama, self-hosted vLLM, etc."""

    def __init__(self, cfg: ModelConfig):
        from openai import OpenAI  # wrapped at the boundary; lazy import

        self.name = cfg.model
        self._cfg = cfg
        self._client = OpenAI(
            base_url=cfg.base_url,
            api_key=os.environ.get("PCIEP_API_KEY", "ollama"),
            timeout=cfg.timeout_s,
        )

    def complete(self, system: str, prompt: str) -> Completion:
        started = time.perf_counter()
        resp = self._client.chat.completions.create(
            model=self._cfg.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=self._cfg.max_tokens,
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        usage = resp.usage
        raw = resp.choices[0].message.content or ""
        return Completion(
            text=strip_reasoning(raw),
            model=self._cfg.model,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
            latency_ms=latency_ms,
        )


class AnthropicClient:
    """Hosted Claude arm — wrapped at the boundary; needs ANTHROPIC_API_KEY."""

    def __init__(self, cfg: ModelConfig):
        from anthropic import Anthropic  # lazy import

        self.name = cfg.model
        self._cfg = cfg
        self._client = Anthropic()

    def complete(self, system: str, prompt: str) -> Completion:
        started = time.perf_counter()
        message = self._client.messages.create(
            model=self._cfg.model,
            max_tokens=self._cfg.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        latency_ms = (time.perf_counter() - started) * 1000.0
        text = "".join(b.text for b in message.content if b.type == "text")
        return Completion(
            text=strip_reasoning(text),
            model=self._cfg.model,
            prompt_tokens=message.usage.input_tokens,
            completion_tokens=message.usage.output_tokens,
            latency_ms=latency_ms,
        )


def client_from_env() -> OpenAICompatibleClient | AnthropicClient:
    cfg = config_from_env()
    if cfg.provider == "anthropic":
        return AnthropicClient(cfg)
    return OpenAICompatibleClient(cfg)


def make_client(entry: dict) -> OpenAICompatibleClient | AnthropicClient:
    """Build a client from a registry entry (pack/models.py)."""
    cfg = ModelConfig(
        provider=entry["provider"],
        model=entry["model"],
        base_url=entry.get("base_url", "http://localhost:11434/v1"),
        max_tokens=int(os.environ.get("PCIEP_MAX_TOKENS", "1024")),
        timeout_s=float(os.environ.get("PCIEP_TIMEOUT", "240")),
    )
    if cfg.provider == "anthropic":
        return AnthropicClient(cfg)
    return OpenAICompatibleClient(cfg)
