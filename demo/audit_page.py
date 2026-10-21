"""Log in as Priya from the security team and screenshot the audit log.

python demo/audit_page.py
"""
from playwright.sync_api import sync_playwright

from two_users import APP, SHOTS, login

with sync_playwright() as p:
    page = p.chromium.launch().new_context(viewport={"width": 1920, "height": 1080}).new_page()
    login(page, "priya")
    page.goto(f"{APP}/audit")
    page.screenshot(path=SHOTS / "07_audit_after_rate_limit.png")
    rows = [[c.strip() for c in r.split("\t")] for r in page.locator("tr").all_inner_texts()[1:]]
print(f"{len(rows)} audit rows, newest first: time, user, question, model, notes")
for r in rows[:12]:
    print(f"  {r[0][11:19]}  {r[1].split('@')[0]:<13} {r[3][:42]:<44} {r[7]:<18} {r[8]}")
