"""Prompt injection: text inside a document that tries to give the model orders.

Two defences live here. scan() flags chunks at ingest so they can be quarantined for a person to
review. spotlight() wraps every source in tags, so the model can tell our instructions from data.
"""
import html
import re

from kb.models import Hit

# Phrases that instruct an AI. Real documents about pumps and leave policies don't talk like this.
PATTERNS = {
    "override": r"\b(ignore|disregard|forget)\b.{0,40}\b(previous|prior|above|earlier|all|your)\b.{0,20}\b(instructions?|rules|prompts?)\b",
    "role_change": r"\byou are now\b|\bact as (an? )?(admin|administrator|developer|dan)\b|\b(support|admin|developer|god) mode\b",
    "fake_system": r"\b(system (instruction|override|prompt|note)|assistant:|<\|im_start\|>|\[/?INST\])",
    "addressed_to_ai": r"\b(note|instructions?|rule)s? for the (ai|assistant|model|llm)\b|\bfor the ai\b",
    "secrecy": r"\bdo not (mention|reveal|tell)\b.{0,30}\b(rule|instruction|this)\b",
    "exfil_markdown": r"!\[[^\]]*\]\(https?://",
    "credential_ask": r"\b(log ?in|sign ?in|verify)\b.{0,80}\b(password|credentials|otp)\b",
}
_COMPILED = {name: re.compile(p, re.I | re.S) for name, p in PATTERNS.items()}


def scan(text: str) -> list[str]:
    """Names of the injection patterns this text matches. Empty means it looks clean."""
    return [name for name, rx in _COMPILED.items() if rx.search(text)]


def spotlight(hits: list[Hit]) -> str:
    """Put each source inside <source> tags, escaping anything that could close the tag early."""
    blocks = []
    for i, h in enumerate(hits, 1):
        body = html.escape(h.text, quote=False)  # a document can't write its own </source>
        blocks.append(f'<source id="{i}" title="{html.escape(h.title)}">\n{body}\n</source>')
    return "\n\n".join(blocks)
