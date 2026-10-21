"""Run inside the app container: which outside addresses can we reach?

docker compose exec app python deploy/egress_check.py
"""
import httpx

TARGETS = ["https://pypi.org/simple/", "https://huggingface.co", "https://example.com",
           "https://api.anthropic.com/v1/models", "http://host.docker.internal:11434/api/version"]

for url in TARGETS:
    for via in ("direct", "proxy"):
        try:
            r = httpx.get(url, timeout=5, trust_env=(via == "proxy"))
            result = f"HTTP {r.status_code}"
        except httpx.HTTPError as e:
            result = f"blocked ({type(e).__name__})"
        print(f"{via:<7} {url:<48} {result}")
