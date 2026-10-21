"""The router falls back to the local model on every kind of cloud failure, and keeps restricted data local."""
import httpx
import pytest

from kb.llm import Provider, Router

OK = {"id": "1", "object": "chat.completion", "created": 0, "model": "m",
      "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hello [1]"}}]}


def provider(name: str, handler, cloud: bool) -> Provider:
    p = Provider(name, "http://test/v1", "m", "k", cloud)
    p.client = p.client.with_options(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    return p


def status(code: int):
    return lambda req: httpx.Response(code, json=OK if code == 200 else {"error": {"message": "x"}})


def down(req):
    raise httpx.ConnectError("no route to host")


MSG = [{"role": "user", "content": "hi"}]


def test_primary_used_when_healthy():
    r = Router(provider("cloud", status(200), True), provider("local", status(200), False))
    assert r.chat(MSG, restricted=False).provider == "cloud"


@pytest.mark.parametrize("failure", [status(401), status(429), status(500), status(503), down])
def test_falls_back_on_failure(failure):
    r = Router(provider("cloud", failure, True), provider("local", status(200), False))
    reply = r.chat(MSG, restricted=False)
    assert reply.provider == "local" and reply.attempts[0].startswith("cloud:")


def test_restricted_data_never_goes_to_the_cloud():
    calls = []
    cloud = provider("cloud", lambda req: calls.append(req) or httpx.Response(200, json=OK), True)
    reply = Router(cloud, provider("local", status(200), False)).chat(MSG, restricted=True)
    assert reply.provider == "local" and calls == []


def test_circuit_opens_after_three_failures_then_retries_after_cooldown():
    now = [0.0]
    calls = []
    cloud = provider("cloud", lambda req: calls.append(1) or httpx.Response(500, json={}), True)
    r = Router(cloud, provider("local", status(200), False), open_after=3, cooldown_s=60, clock=lambda: now[0])
    for _ in range(5):
        r.chat(MSG, restricted=False)
    assert len(calls) == 3  # the 4th and 5th questions skip the broken cloud entirely
    now[0] = 61
    r.chat(MSG, restricted=False)
    assert len(calls) == 4


def test_everything_down_is_an_error_not_a_made_up_answer():
    r = Router(provider("cloud", down, True), provider("local", down, False))
    with pytest.raises(RuntimeError):
        r.chat(MSG, restricted=False)
