"""Check every answer before it leaves: no leaked instructions, no outside links, no identifiers."""
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from kb.pii import redact

# links are allowed only to the company's own systems
ALLOWED_HOSTS = ("vardhanpumps.in", "docs.google.com", "vardhanpumps.atlassian.net")
BLOCKED = "I can't share that answer. It has been logged for the security team."

MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
URL = re.compile(r"https?://[^\s)\]>\"']+")
# the red team found this one: a model happily writes "vpn-vardhan.help" with no http:// in front
BARE_DOMAIN = re.compile(r"(?<![@\w.-])((?:[a-z0-9-]+\.)+(?:com|co|in|net|org|io|ai|app|dev|help|info|xyz|site|online|link))\b", re.I)
# our assistant never asks anyone for a password, so an answer that does was written by an attacker
ASKS_FOR_PASSWORD = re.compile(r"\b(password|passcode|otp|pin)\b", re.I)


@dataclass
class Checked:
    text: str
    actions: list[str] = field(default_factory=list)  # what the guard changed, for the audit log
    blocked: bool = False


def allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def check_answer(text: str, canary: str) -> Checked:
    if canary in text:  # the model is repeating its own system prompt
        return Checked(BLOCKED, ["system_prompt_leak"], blocked=True)
    if ASKS_FOR_PASSWORD.search(text):
        return Checked(BLOCKED, ["asks_for_password"], blocked=True)
    out = Checked(text)
    if MD_IMAGE.search(out.text):  # an image URL is fetched by the browser: a silent data leak
        out.text = MD_IMAGE.sub("", out.text)
        out.actions.append("removed_image")
    for url in URL.findall(out.text):
        if not allowed(url):
            out.text = out.text.replace(url, "(link removed)")
            out.actions.append(f"removed_link:{urlparse(url).hostname}")
    for host in BARE_DOMAIN.findall(out.text):
        if not allowed(f"http://{host}"):
            out.text = out.text.replace(host, "(link removed)")
            out.actions.append(f"removed_link:{host}")
    out.text, counts = redact(out.text)
    out.actions += [f"redacted:{k}" for k in counts]
    return out
