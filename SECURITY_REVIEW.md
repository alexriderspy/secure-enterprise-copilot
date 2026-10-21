# Security review checklist

The questions an enterprise security team asks before an AI assistant touches company data, and where
this repo answers each one. "Evidence" is something a reviewer can run.

| # | Question | What we built | Code | Evidence |
|---|---|---|---|---|
| 1 | How do users log in? | Company SSO over OIDC, code flow with PKCE. The app never sees a password. Tokens verified for signature, issuer, audience and expiry | `app/auth.py` | `tests/test_auth.py` (no token, forged key, wrong audience, expired: all 401) |
| 2 | Can a user see documents they couldn't open in Drive or Jira? | ACLs copied from the source at ingest; the permission filter is inside the SQL query, checked again in Python | `kb/connectors/`, `kb/store.py`, `kb/retrieve.py` | `tests/test_retrieval.py`, `tests/test_llm_leak.py`, red-team "cross-user leak" |
| 3 | What happens to personal data? | Presidio masks Aadhaar, PAN, phone, personal email, bank account, UPI and card numbers on ingest, on every answer, and in the audit log | `kb/pii.py`, `kb/guard.py`, `kb/audit.py` | `tests/test_pii.py`, red-team "identifier extraction" |
| 4 | Can a document hijack the model? | Ingest scanner quarantines instruction-like chunks for review; sources wrapped in `<source>` tags; the model has no tools, so it can only write text | `kb/injection.py`, `kb/answer.py` | `tests/test_injection.py`, `tests/test_llm_injection.py`, red-team "injected document" |
| 5 | What does the output filter do? | Blocks answers containing the system-prompt canary, removes outside links and all images, masks identifiers, drops uncited answers | `kb/guard.py`, `kb/answer.py` | `tests/test_guard.py` |
| 6 | Is there an audit trail? | One append-only row per question: user, groups, masked question, retrieved, denied, cited, model used, guard actions | `kb/audit.py` | audit page (security-admins only), `tests/test_auth.py` (403 for others) |
| 7 | Can one user abuse it? | Token bucket per user, 10 questions a minute, then 429 with Retry-After; question length capped at 500 | `app/ratelimit.py`, `app/main.py` | `tests/test_ratelimit.py`, `demo/rate_limit.py` |
| 8 | Where are the secrets? | Docker secrets mounted as files, never in the image or env dumps; `Secret` never prints; log filter masks login codes, bearer tokens and secrets | `kb/config.py`, `app/logsafe.py`, `.dockerignore` | `tests/test_secrets.py` |
| 9 | What can the deployment talk to? | App and Keycloak on an internal Docker network with no route out; the only exit is an egress proxy that allows two hosts | `docker-compose.yml`, `deploy/egress/` | `deploy/egress_check.py` output, proxy logs |
| 10 | Does company data go to a third-party model? | Only documents shared with the whole company may go to the cloud model; anything restricted is answered by the local open-weight model | `kb/llm.py`, `kb/store.py` | `tests/test_router.py` |
| 11 | What if the model vendor is down? | Router falls back to local qwen2.5:7b on connection errors, timeouts, 401, 429 and 5xx; circuit breaker after 3 failures | `kb/llm.py` | `tests/test_router.py`, fallback demo |
| 12 | Is the container hardened? | Non-root user, read-only filesystem, all capabilities dropped, no-new-privileges, memory limits | `deploy/Dockerfile`, `docker-compose.yml` | `docker inspect` |
| 13 | How do you know it works? | Unit tests, LLM tests, and a red-team eval with before/after numbers | `tests/`, `evals/` | `python -m evals.redteam` |

## Known gaps (say these out loud in the review)

- No TLS here. In production the gateway terminates HTTPS, which also turns on the `secure` cookie flag.
- Keycloak runs in `start-dev` mode. Production: `start` with a real database, or the company's own IdP.
- The audit log is SQLite with append-only triggers. Production: also ship rows to a write-once store (SIEM, S3 Object Lock).
- The injection scanner is pattern-based. New phrasings get past it, which is why spotlighting, the output guard and "no tools" sit behind it. A trained classifier can replace `scan()`.
- Permissions are copied at ingest, so a revoked share lasts until the next sync.
- Rate limits live in process memory. With several app servers, move them to Redis.
