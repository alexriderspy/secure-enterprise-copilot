"""Through the real LLM, with every defence on: the planted instructions never reach the user.

pytest -m llm
"""
import pytest

from evals.attacks import ATTACKS
from kb.answer import answer
from kb.retrieve import retrieve
from tests.conftest import USERS

pytestmark = pytest.mark.llm
INJECTED = [a for a in ATTACKS if a.category.startswith("injected") or a.category == "identifier extraction"]


@pytest.mark.parametrize("attack", INJECTED, ids=lambda a: f"{a.user}: {a.question}")
def test_attack_does_not_work(store, attack):
    hits = retrieve(store, USERS[attack.user], attack.question).hits
    assert not attack.worked(answer(attack.question, hits, restricted=True).text)
