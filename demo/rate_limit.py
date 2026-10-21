"""Log in as Rohan, then send 12 questions at once. The first 10 get answers, the rest get 429.

python demo/rate_limit.py
"""
from concurrent.futures import ThreadPoolExecutor

import httpx
from playwright.sync_api import sync_playwright

from two_users import APP, login

with sync_playwright() as p:
    page = p.chromium.launch().new_context().new_page()
    login(page, "rohan")
    token = next(c["value"] for c in page.context.cookies() if c["name"] == "kb_token")


def one(i: int) -> str:
    r = httpx.post(f"{APP}/api/ask", json={"question": "What is the list price of the VP-100?"},
                   headers={"Authorization": f"Bearer {token}"}, timeout=600, trust_env=False)
    return f"request {i:>2}: HTTP {r.status_code}" + (f"  Retry-After {r.headers['retry-after']}s" if r.status_code == 429 else "")


with ThreadPoolExecutor(max_workers=12) as pool:
    for line in pool.map(one, range(1, 13)):
        print(line)
