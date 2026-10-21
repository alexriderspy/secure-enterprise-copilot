"""All settings come from the environment. Secrets can also come from files (Docker secrets)."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


class Secret:
    """Holds a secret without ever printing it, in logs, errors or tracebacks."""

    def __init__(self, value: str):
        self._value = value

    def get(self) -> str:
        return self._value

    def __bool__(self) -> bool:
        return bool(self._value)

    def __repr__(self) -> str:
        return "Secret('********')" if self._value else "Secret('')"

    __str__ = __repr__


def secret(name: str) -> Secret:
    """NAME_FILE points at a file (Docker mounts secrets under /run/secrets), else NAME from the env."""
    path = os.getenv(f"{name}_FILE")
    if not path:
        return Secret(os.getenv(name, ""))
    file = Path(path) if Path(path).is_absolute() else ROOT / path
    return Secret(file.read_text().strip() if file.exists() else "")


@dataclass(frozen=True)
class Settings:
    db_path: Path = Path(os.getenv("KB_DB", ROOT / "kb.db"))
    embed_model: str = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    # primary: any OpenAI-compatible cloud API. Leave the URL empty to run fully local.
    llm_primary_base_url: str = os.getenv("LLM_PRIMARY_BASE_URL", "")
    llm_primary_model: str = os.getenv("LLM_PRIMARY_MODEL", "")
    llm_primary_api_key: Secret = secret("LLM_PRIMARY_API_KEY")
    # fallback: the open-weight model on our own machine
    llm_fallback_base_url: str = os.getenv("LLM_FALLBACK_BASE_URL", "http://localhost:11434/v1")
    llm_fallback_model: str = os.getenv("LLM_FALLBACK_MODEL", "qwen2.5:7b")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "60"))
    oidc_issuer: str = os.getenv("OIDC_ISSUER", "http://localhost:8080/realms/vardhan")
    oidc_discovery_url: str = os.getenv("OIDC_DISCOVERY_URL", "")  # inside Docker: the internal address
    oidc_client_id: str = os.getenv("OIDC_CLIENT_ID", "kb-app")
    oidc_client_secret: Secret = secret("OIDC_CLIENT_SECRET")
    app_url: str = os.getenv("APP_URL", "http://localhost:8000")
    company_domain: str = os.getenv("COMPANY_DOMAIN", "vardhanpumps.in")
    audit_group: str = os.getenv("AUDIT_GROUP", "security-admins")
    rate_per_minute: int = int(os.getenv("RATE_PER_MINUTE", "10"))


settings = Settings()
