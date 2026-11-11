"""Thin LLM wrapper. Uses Claude when ANTHROPIC_API_KEY is set, otherwise None.

Every agent in this project has a deterministic offline fallback, so the
whole pipeline (and the test suite) runs without an API key.
"""
from __future__ import annotations

import os

DEFAULT_MODEL = os.environ.get("WIKI_MODEL", "claude-haiku-5-5")


def available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def complete(system: str, prompt: str, max_tokens: int = 1200) -> str | None:
    """Return the model's text, or None if no model is configured."""
    if not available():
        return None
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
