"""Run every attack and every normal question against three setups and count what got through.

python -m evals.redteam
"""
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path

os.environ["LLM_PRIMARY_BASE_URL"] = ""  # the eval measures the defences, on the local model only

from evals.attacks import ATTACKS, USEFUL  # noqa: E402
from kb.answer import answer  # noqa: E402
from kb.defences import ALL_ON, NONE, Defences  # noqa: E402
from kb.ingest import ingest  # noqa: E402
from kb.retrieve import retrieve  # noqa: E402
from kb.store import Store  # noqa: E402
from tests.conftest import USERS  # noqa: E402

SETUPS = {
    "week 9 (no defences)": NONE,
    "+ prompt and output": Defences(redact_ingest=True, scan_ingest=False, spotlight=True, guard_output=True),
    "all defences": ALL_ON,
}


def run(store: Store, d: Defences, user: str, question: str) -> str:
    hits = retrieve(store, USERS[user], question).hits
    ids = list(dict.fromkeys(h.doc_id for h in hits))
    return answer(question, hits, restricted=bool(ids) and store.is_restricted(ids), d=d).text


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    results: dict = {}
    for name, d in SETUPS.items():
        store = Store(tmp / f"{name[:5]}.db")
        ingest(store, d, verbose=False)
        worked = defaultdict(int)
        log = []
        for a in ATTACKS:
            out = run(store, d, a.user, a.question)
            ok = a.worked(out)
            worked[a.category] += ok
            log.append({"category": a.category, "user": a.user, "question": a.question, "worked": ok, "answer": out})
        useful = sum(expected in run(store, d, u, q) for u, q, expected in USEFUL)
        results[name] = {"worked": dict(worked), "total_worked": sum(worked.values()), "useful": useful, "log": log}
        print(f"{name}: {sum(worked.values())}/{len(ATTACKS)} attacks worked, {useful}/{len(USEFUL)} normal questions right")

    cats = list(dict.fromkeys(a.category for a in ATTACKS))
    n = {c: sum(a.category == c for a in ATTACKS) for c in cats}
    print(f"\n{'attacks that worked':<40}" + "".join(f"{s:>24}" for s in SETUPS))
    for c in cats:
        print(f"{c:<40}" + "".join(f"{str(results[s]['worked'].get(c, 0)) + '/' + str(n[c]):>24}" for s in SETUPS))
    print(f"{'total':<40}" + "".join(f"{str(results[s]['total_worked']) + '/' + str(len(ATTACKS)):>24}" for s in SETUPS))
    print(f"{'normal questions answered right':<40}" + "".join(f"{str(results[s]['useful']) + '/' + str(len(USEFUL)):>24}" for s in SETUPS))
    Path(__file__).with_name("results.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
