"""Pull every document from every connector, quarantine injections, mask identifiers, embed, store.

python -m kb.ingest
"""
import re

from kb.config import ROOT, settings
from kb.connectors.base import Connector
from kb.connectors.drive import DriveConnector, FixtureDrive
from kb.connectors.jira import FixtureJira, JiraConnector
from kb.defences import ALL_ON, Defences
from kb.embed import embed_docs
from kb.injection import scan
from kb.pii import redact
from kb.store import Store


def chunk(title: str, text: str) -> list[str]:
    """One chunk per '## ' section, each starting with the document title so it makes sense alone."""
    parts = [p.strip() for p in re.split(r"\n(?=## )", text) if p.strip()]
    return [f"{title}\n{p}" for p in parts]


def connectors() -> list[Connector]:
    fixtures = ROOT / "data" / "fixtures"
    return [DriveConnector(FixtureDrive(fixtures / "drive"), settings.company_domain),
            JiraConnector(FixtureJira(fixtures / "jira"), "https://vardhanpumps.atlassian.net")]


def prepare(chunks: list[str], d: Defences) -> tuple[list[str], list[tuple[str, list[str]]], dict[str, int]]:
    """Split chunks into clean ones (identifiers masked) and quarantined ones (with the reasons)."""
    clean, quarantined, masked = [], [], {}
    for c in chunks:
        reasons = scan(c) if d.scan_ingest else []
        if reasons:
            quarantined.append((c, reasons))
            continue
        if d.redact_ingest:
            c, counts = redact(c)
            for k, v in counts.items():
                masked[k] = masked.get(k, 0) + v
        clean.append(c)
    return clean, quarantined, masked


def ingest(store: Store, d: Defences = ALL_ON, verbose: bool = True) -> None:
    say = print if verbose else (lambda *a: None)
    masked_total: dict[str, int] = {}
    for conn in connectors():
        n_docs = n_chunks = 0
        for doc in conn.documents():
            if not doc.acl:
                say(f"  skipped {doc.id}: no one is allowed to read it")
                continue
            clean, quarantined, masked = prepare(chunk(doc.title, doc.text), d)
            for _, reasons in quarantined:
                say(f"  quarantined a chunk of {doc.id}: {', '.join(reasons)}")
            for k, v in masked.items():
                masked_total[k] = masked_total.get(k, 0) + v
            # shared with the whole company = internal; anything narrower = restricted
            label = "internal" if f"domain:{settings.company_domain}" in doc.acl else "restricted"
            store.upsert(doc, clean, embed_docs(clean) if clean else [], label, quarantined)
            n_docs, n_chunks = n_docs + 1, n_chunks + len(clean)
        say(f"{conn.name}: {n_docs} documents, {n_chunks} chunks")
    say(f"identifiers masked: {masked_total}")
    say(store.stats())


if __name__ == "__main__":
    ingest(Store(settings.db_path))
