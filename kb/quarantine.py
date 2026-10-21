"""List the chunks ingest quarantined, for a person on the security team to review.

python -m kb.quarantine
"""
from kb.config import settings
from kb.store import Store

rows = Store(settings.db_path).db.execute("SELECT doc_id, title, reasons, text FROM quarantine ORDER BY doc_id").fetchall()
print(f"{len(rows)} quarantined chunks\n")
for doc_id, title, reasons, text in rows:
    print(f"{doc_id}  ({reasons})\n  {title}")
    body = text.split("\n", 1)[1] if "\n" in text else text
    for line in body.strip().splitlines():
        print(f"  | {line[:130]}")
    print()
