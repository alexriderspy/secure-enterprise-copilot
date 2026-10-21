"""Find and mask personal identifiers with Microsoft Presidio, including Indian ones.

We mask identifiers (Aadhaar, PAN, phone, personal email, bank account, UPI, card numbers) and keep
people's names, because "who owns this ticket" is exactly what colleagues search for.
"""
import re
from functools import lru_cache

import tldextract
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import InAadhaarRecognizer, InPanRecognizer

from kb.config import settings

ENTITIES = ["IN_AADHAAR", "IN_PAN", "PHONE_NUMBER", "EMAIL_ADDRESS", "IN_BANK_ACCOUNT", "IN_UPI", "CREDIT_CARD"]
MIN_SCORE = 0.5

# Presidio checks email domains with tldextract, which downloads the public suffix list on first use.
# Our egress proxy blocked that download in the private deployment, so use the copy bundled with the library.
tldextract.tldextract.TLD_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)


@lru_cache(maxsize=1)
def analyzer() -> AnalyzerEngine:
    # spaCy gives Presidio tokens and lemmas, so context words like "account" can raise a score
    nlp = NlpEngineProvider(nlp_configuration={
        "nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]}).create_engine()
    engine = AnalyzerEngine(nlp_engine=nlp, supported_languages=["en"])
    engine.registry.add_recognizer(InAadhaarRecognizer())   # 12 digits + Verhoeff checksum
    engine.registry.add_recognizer(InPanRecognizer())       # AAAPA1234A
    engine.registry.add_recognizer(PatternRecognizer(
        supported_entity="IN_UPI", patterns=[Pattern("upi", r"\b[\w.\-]{2,64}@(ok\w+|ybl|ibl|axl|paytm|upi)\b", 0.8)]))
    engine.registry.add_recognizer(PatternRecognizer(
        supported_entity="IN_BANK_ACCOUNT", patterns=[Pattern("acct", r"\b\d{9,18}\b", 0.3)],
        context=["account", "a/c", "acct", "bank"]))  # only counts next to these words
    return engine


def find(text: str) -> list[RecognizerResult]:
    results = analyzer().analyze(text, language="en", entities=ENTITIES, score_threshold=MIN_SCORE)
    work_email = re.compile(rf"@{re.escape(settings.company_domain)}$", re.I)
    results = [r for r in results if not (r.entity_type == "EMAIL_ADDRESS" and work_email.search(text[r.start:r.end]))]
    # keep the longest, highest-scoring span when two overlap
    results.sort(key=lambda r: (r.start, -(r.end - r.start), -r.score))
    kept: list[RecognizerResult] = []
    for r in results:
        if not kept or r.start >= kept[-1].end:
            kept.append(r)
    return kept


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Replace every identifier with a placeholder like <IN_AADHAAR>. Returns the text and counts."""
    counts: dict[str, int] = {}
    for r in sorted(find(text), key=lambda r: r.start, reverse=True):
        text = text[:r.start] + f"<{r.entity_type}>" + text[r.end:]
        counts[r.entity_type] = counts.get(r.entity_type, 0) + 1
    return text, counts


if __name__ == "__main__":  # python -m kb.pii <file>: show what gets masked
    import sys
    from pathlib import Path

    masked, counts = redact(Path(sys.argv[1]).read_text())
    print(masked, "\n", counts, sep="")
