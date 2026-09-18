# Okapi Copilot

Intelligence, orchestration, knowledge and governed-automation platform
for the Okapi SaaS ecosystem. See project Documents 1–11 for the full
normative specification; this README covers only how the codebase is
organized and how to run it.

## Status

Phase 0 (architecture skeleton) complete. Phase 1 (Secure Intelligent
Runtime, Document 3) in progress — security foundation slice landed:

| Capability | Status | Evidence |
|---|---|---|
| DDD/hexagonal skeleton | IMPLEMENTED | `src/okapi_copilot/`, CI purity guard (local; not yet pushed, see below) |
| `SecurityContext` value object | IMPLEMENTED | `domain/security/security_context.py`, `tests/unit/domain/test_security_context.py` |
| Identity domain (`User`, `ChannelIdentity`, `MembershipReference`) | IMPLEMENTED | `domain/identity/`, `tests/unit/domain/identity/` |
| Keycloak token verification (signature/issuer/audience/expiry) | IMPLEMENTED | `infrastructure/identity/keycloak_identity_provider.py`, tested with real RSA crypto in `tests/unit/infrastructure/identity/` |
| `ResolveSecurityContext` use case (tenant/org resolution, ambiguity handling) | IMPLEMENTED | `application/use_cases/resolve_security_context.py`, `tests/unit/application/use_cases/` |
| HTTP middleware wiring `ResolveSecurityContext` into requests | MISSING | not started — see Known Gaps |
| Membership persistence (SurrealDB-backed repository) | UNVERIFIED | `infrastructure/persistence/surrealdb/`, query/mapping logic unit-tested against a fake connection; **not exercised against a live SurrealDB server** |
| Policy Engine (`DefaultPolicyEngine`) | PARTIALLY_IMPLEMENTED | `infrastructure/policy/default_policy_engine.py` — returns real ALLOW/DENY decisions; REQUIRE_CONFIRMATION/APPROVAL/HUMAN outcomes not implemented (see Known Gaps) |
| Role → permission expansion | MISSING | `permissions_snapshot` is currently always empty |

This matrix is maintained by hand as work lands — it is not
auto-generated, so treat it as a claim to verify against the tests
referenced, per Document 11's evidence requirement.

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

- `KeycloakIdentityProvider` (`infrastructure/identity/`) is implemented
  and tested against real signed JWTs, but is **not yet wired into the
  HTTP layer**. Wiring it now would require a working end-to-end path
  including `MembershipRepository`, which is UNVERIFIED (see next
  point) — shipping HTTP-facing security backed by an unverified
  persistence layer would look like working security without solid
  ground underneath it. That is exactly the "no false certification"
  failure mode this project's audit skill exists to prevent, so it
  stays unwired until the SurrealDB adapter has been run against a real
  server.
- `SurrealDbMembershipRepository` (`infrastructure/persistence/surrealdb/`)
  is implemented — parameterized queries, row mapping, malformed-row
  handling — and unit-tested against a **fake** connection object. It
  has **never been run against an actual SurrealDB server**: no
  SurrealDB instance is reachable from the environment this code was
  written in. Wire-protocol compatibility is UNVERIFIED. Before relying
  on this in any environment, run it against `docker compose up
  surrealdb` (or a real deployment) and add an integration test.
- `DefaultPolicyEngine` (`infrastructure/policy/`) only ever returns
  ALLOW or DENY. Document 3 Section 40 also specifies
  REQUIRE_CONFIRMATION, REQUIRE_APPROVAL, and REQUIRE_HUMAN as policy
  outcomes; producing those correctly needs the Risk Engine,
  Confirmation Engine, Approval Engine, and Human Handoff policy, none
  of which exist yet. Do not wire this engine in front of a critical
  mutation until those exist — it is only correct today for operations
  low-risk enough to never need confirmation/approval. It also does not
  implement the "capability inconnue" / "policy inconnue" DENY BY
  DEFAULT cases from Document 3 Section 43 — there is no Capability
  Registry or versioned policy store yet.
- No SurrealDB repository adapters exist yet for anything other than
  `MembershipRepository`.
- No event publisher (RabbitMQ) adapter yet.
- `/health/ready` reports `not_wired` for all dependencies until the
  above adapters are wired and verified — this is intentional; do not
  fake a healthy readiness response before the checks are real.
- CI workflow (`.github/workflows/ci.yml`) exists on disk but has not
  been pushed to the remote — the token used for the initial push
  lacked the `workflow` OAuth scope GitHub requires to accept workflow
  files. Push it once a token with that scope is available, or add it
  via the GitHub UI. Note it currently only runs `mypy` on
  `domain`+`application`; the whole of `src/` now passes `mypy --strict`
  (verified locally), so the workflow's scope should be widened to
  `src/okapi_copilot` when it is pushed.

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
