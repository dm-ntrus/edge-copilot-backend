# Okapi Copilot

Intelligence, orchestration, knowledge and governed-automation platform
for the Okapi SaaS ecosystem. See project Documents 1–11 for the full
normative specification; this README covers only how the codebase is
organized and how to run it.

## Status

Architecture skeleton only. No business features are implemented yet.
See `docs/` (to be added) or the project's audit trail for the current
capability matrix (IMPLEMENTED / PARTIALLY_IMPLEMENTED / MISSING /
BROKEN / UNVERIFIED per Document 11).

## Architecture

DDD + Hexagonal, per Document 2 Section 5 and the Architecture Guardian
skill:

```
src/okapi_copilot/
├── interfaces/       # FastAPI HTTP layer. The ONLY package allowed to
│                      import FastAPI/Starlette directly.
├── application/       # Use cases + ports (Protocols). Orchestrates the
│                      domain; depends only on ports, never on concrete
│                      infrastructure.
├── domain/             # Pure business rules. Zero framework, zero DB,
│                      zero provider SDK imports. Enforced by CI
│                      ("Domain purity check").
└── infrastructure/    # Adapters implementing the ports (SurrealDB,
                       Redis, RabbitMQ, Keycloak, observability).
```

Dependency direction: `interfaces -> application -> domain <- infrastructure`.
Infrastructure implements ports defined by `application`; it never
reaches into `domain` internals beyond what the ports expose.

## Reference stack (Document 2 Section 6)

| Concern        | Choice                          |
|----------------|----------------------------------|
| Language       | Python 3.11+                    |
| API            | FastAPI                         |
| Database       | SurrealDB                       |
| Cache          | Redis                           |
| Identity       | Keycloak                        |
| Messaging      | RabbitMQ (or compatible broker) |
| Observability  | OpenTelemetry                   |
| API contract   | OpenAPI                         |

This is a reference implementation of the stack, not an absolute
architectural dependency (Document 2 Section 6) — ports exist precisely
so any of these can be swapped without touching `domain/` or
`application/`.

## Security posture (do not weaken without updating this section)

- `SecurityContext` (`domain/security/security_context.py`) is an
  immutable value object. It is never constructed from untrusted input
  directly — see `application/ports/identity_provider.py` and
  `application/ports/policy_engine.py` for the trusted issuance /
  authorization path.
- `X-Tenant-ID` / `X-Organization-ID` headers are read by the HTTP layer
  as *metadata* only. They are never treated as proof of authorization
  (Document 9 Section 15). The security-context-resolution middleware
  that validates them against a real, server-issued context is not yet
  implemented — see Known Gaps below.
- Authentication (Keycloak) and Authorization (Policy Engine) are
  separate ports and must remain separate calls.

## Known gaps (explicitly tracked, not silently assumed away)

- No adapter yet implements `IdentityProvider` against real Keycloak.
- No adapter yet implements `PolicyEngine`.
- No SurrealDB repository adapters yet.
- No event publisher (RabbitMQ) adapter yet.
- `/health/ready` reports `not_wired` for all dependencies until the
  above adapters exist — this is intentional; do not fake a healthy
  readiness response before the checks are real.

## Running locally

```bash
cp .env.example .env
docker compose up --build
```

The API will be available at `http://localhost:8000`. `GET /health/live`
should return `200`.

## Development

```bash
pip install -e ".[dev]"
ruff check src tests
mypy src/okapi_copilot/domain src/okapi_copilot/application
pytest --cov=okapi_copilot
```

CI (`.github/workflows/ci.yml`) runs the same checks, plus a guard that
fails the build if the domain layer imports a framework or provider SDK.
