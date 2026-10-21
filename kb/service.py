"""One question, end to end: retrieve with permissions, answer, write the audit row."""
import time

from kb.answer import Answer, answer
from kb.audit import AuditLog
from kb.defences import ALL_ON, Defences
from kb.injection import scan
from kb.models import Principal
from kb.retrieve import retrieve
from kb.store import Store


def ask(store: Store, audit: AuditLog, user: Principal, question: str,
        d: Defences = ALL_ON) -> tuple[Answer, list[str]]:
    t0 = time.perf_counter()
    r = retrieve(store, user, question)
    doc_ids = list(dict.fromkeys(h.doc_id for h in r.hits))
    ans = answer(question, r.hits, restricted=bool(doc_ids) and store.is_restricted(doc_ids), d=d)
    notes = [f"question_flagged:{x}" for x in scan(question)] + ans.notes
    audit.log(user, question, retrieved=doc_ids, denied=r.denied,
              cited=list(dict.fromkeys(h.doc_id for _, h in ans.cited)),
              ms=int((time.perf_counter() - t0) * 1000), provider=ans.provider, notes=notes)
    return ans, r.denied
