"""Model routing: the cloud model first, our own open-weight model when the cloud fails.

Restricted documents (anything not shared with the whole company) never go to the cloud at all.
"""
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

import openai

from kb.config import settings


@dataclass
class Provider:
    name: str
    base_url: str
    model: str
    api_key: str
    cloud: bool
    timeout_s: float = 60

    def __post_init__(self) -> None:
        # max_retries=0: the router decides what happens on failure, not the SDK
        self.client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key or "none",
                                    timeout=self.timeout_s, max_retries=0)


@dataclass
class Reply:
    text: str
    provider: str
    attempts: list[str] = field(default_factory=list)  # every provider we tried and why it failed


class Router:
    def __init__(self, primary: Provider | None, fallback: Provider, open_after: int = 3,
                 cooldown_s: float = 60, clock: Callable[[], float] = time.monotonic):
        self.primary, self.fallback = primary, fallback
        self.open_after, self.cooldown_s, self.clock = open_after, cooldown_s, clock
        self.failures, self.open_until = 0, 0.0

    def order(self, restricted: bool, attempts: list[str]) -> list[Provider]:
        if self.primary is None:
            return [self.fallback]
        if restricted:
            attempts.append(f"{self.primary.name}: skipped, restricted data stays local")
            return [self.fallback]
        if self.clock() < self.open_until:  # circuit breaker: the cloud failed a lot just now
            attempts.append(f"{self.primary.name}: skipped, circuit open")
            return [self.fallback]
        return [self.primary, self.fallback]

    def chat(self, messages: list[dict], restricted: bool) -> Reply:
        attempts: list[str] = []
        for p in self.order(restricted, attempts):
            try:
                resp = p.client.chat.completions.create(model=p.model, messages=messages, temperature=0)
            except openai.APIError as e:  # connection errors, timeouts, 401, 429, 5xx
                attempts.append(f"{p.name}: {type(e).__name__}")
                if p is self.primary:
                    self.failures += 1
                    if self.failures >= self.open_after:
                        self.open_until = self.clock() + self.cooldown_s
                continue
            if p is self.primary:
                self.failures = 0
            return Reply(resp.choices[0].message.content.strip(), p.name, attempts)
        raise RuntimeError(f"every model failed: {attempts}")


@lru_cache(maxsize=1)
def router() -> Router:
    s = settings
    primary = Provider("cloud:" + s.llm_primary_model, s.llm_primary_base_url, s.llm_primary_model,
                       s.llm_primary_api_key.get(), cloud=True, timeout_s=s.llm_timeout_s) if s.llm_primary_base_url else None
    fallback = Provider("local:" + s.llm_fallback_model, s.llm_fallback_base_url, s.llm_fallback_model,
                        "ollama", cloud=False, timeout_s=s.llm_timeout_s)
    return Router(primary, fallback)
