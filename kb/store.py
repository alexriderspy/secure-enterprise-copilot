"""SQLite holds the chunks, their vectors and the ACL. The permission filter is part of the SQL query,
so chunks a user can't read never even leave the database."""
import sqlite3
from pathlib import Path

import numpy as np

from kb.models import Hit, SourceDoc

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, source TEXT, title TEXT, url TEXT, updated TEXT,
                                     classification TEXT);
CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, doc_id TEXT REFERENCES documents(id), text TEXT, vec BLOB);
CREATE TABLE IF NOT EXISTS acl (doc_id TEXT REFERENCES documents(id), principal TEXT);
CREATE INDEX IF NOT EXISTS acl_principal ON acl(principal);
CREATE TABLE IF NOT EXISTS quarantine (doc_id TEXT, title TEXT, text TEXT, reasons TEXT);
"""


class Store:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.executescript(SCHEMA)

    def upsert(self, doc: SourceDoc, chunks: list[str], vecs: np.ndarray, classification: str,
               quarantined: list[tuple[str, list[str]]] = ()) -> None:
        with self.db:
            for table, col in (("chunks", "doc_id"), ("acl", "doc_id"), ("quarantine", "doc_id"), ("documents", "id")):
                self.db.execute(f"DELETE FROM {table} WHERE {col} = ?", (doc.id,))
            self.db.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
                            (doc.id, doc.source, doc.title, doc.url, doc.updated, classification))
            self.db.executemany("INSERT INTO quarantine VALUES (?, ?, ?, ?)",
                                [(doc.id, doc.title, text, ",".join(r)) for text, r in quarantined])
            self.db.executemany("INSERT INTO chunks (doc_id, text, vec) VALUES (?, ?, ?)",
                                [(doc.id, c, v.astype(np.float32).tobytes()) for c, v in zip(chunks, vecs)])
            self.db.executemany("INSERT INTO acl VALUES (?, ?)", [(doc.id, p) for p in sorted(doc.acl)])

    def search(self, qvec: np.ndarray, principals: set[str], k: int = 4, allowed: bool = True) -> list[Hit]:
        """Top-k chunks among the documents these principals can read (or, for the audit, can't)."""
        marks = ",".join("?" * len(principals))
        op = "IN" if allowed else "NOT IN"
        rows = self.db.execute(f"""
            SELECT c.id, c.doc_id, d.title, d.url, c.text, c.vec FROM chunks c JOIN documents d ON d.id = c.doc_id
            WHERE c.doc_id {op} (SELECT doc_id FROM acl WHERE principal IN ({marks}))""",
            sorted(principals)).fetchall()
        if not rows:
            return []
        vecs = np.stack([np.frombuffer(r[5], dtype=np.float32) for r in rows])
        scores = vecs @ qvec  # vectors are normalised, so this is cosine similarity
        best = np.argsort(-scores)[:k]
        return [Hit(rows[i][0], rows[i][1], rows[i][2], rows[i][3], rows[i][4], float(scores[i])) for i in best]

    def is_restricted(self, doc_ids: list[str]) -> bool:
        marks = ",".join("?" * len(doc_ids))
        return self.db.execute(f"SELECT COUNT(*) FROM documents WHERE id IN ({marks}) AND classification != 'internal'",
                               doc_ids).fetchone()[0] > 0

    def quarantined(self) -> list[tuple[str, str]]:
        return self.db.execute("SELECT doc_id, reasons FROM quarantine ORDER BY doc_id").fetchall()

    def acl_of(self, doc_id: str) -> set[str]:
        return {r[0] for r in self.db.execute("SELECT principal FROM acl WHERE doc_id = ?", (doc_id,))}

    def stats(self) -> dict:
        q = lambda sql: self.db.execute(sql).fetchone()[0]
        return {"documents": q("SELECT COUNT(*) FROM documents"), "chunks": q("SELECT COUNT(*) FROM chunks"),
                "acl_rows": q("SELECT COUNT(*) FROM acl"), "quarantined": q("SELECT COUNT(*) FROM quarantine")}
