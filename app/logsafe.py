"""Keep secrets out of the logs: one-time login codes, tokens and our configured secrets."""
import logging
import re

from kb.config import settings

URL_PARAMS = re.compile(r"\b(code|state|session_state)=[^&\s\"]+")
BEARER = re.compile(r"Bearer [\w\-.]+")


def clean(text: str) -> str:
    text = BEARER.sub("Bearer ***", URL_PARAMS.sub(r"\1=***", text))
    for s in (settings.oidc_client_secret, settings.llm_primary_api_key):
        if s:
            text = text.replace(s.get(), "***")
    return text


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = clean(record.msg)
        if isinstance(record.args, tuple):  # uvicorn puts the request path in the args
            record.args = tuple(clean(a) if isinstance(a, str) else a for a in record.args)
        return True


def install() -> None:
    for name in ("uvicorn.access", "uvicorn.error"):
        logging.getLogger(name).addFilter(RedactingFilter())
