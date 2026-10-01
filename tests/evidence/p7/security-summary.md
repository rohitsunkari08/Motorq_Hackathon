# EV Fleet Security Scan Summary (NOTE.md §8 / §9 / §16)

Generated: 2026-10-01 08:15:00 UTC

## 1. Vulnerability & Scan Metrics Overview

| Scanner | Target / Scope | Critical | High | Medium | Low | Audit Status |
|---|---|---|---|---|---|---|
| **Semgrep SAST** | Python & Go source code (`services/`) | 0 | 0 | 0 | 2 (Informational) | **CLEAN / PASSED** |
| **Gitleaks** | Git repository commits, trees, and env files | 0 | 0 | 0 | 0 | **CLEAN / PASSED** |
| **Trivy FS & Image** | Container root filesystems & base images | 0 | 0 | 1 | 3 | **CLEAN / PASSED** |
| **govulncheck** | Go dependencies (`services/simulator`, `services/ingest`) | 0 | 0 | 0 | 0 | **CLEAN / PASSED** |
| **pip-audit** | Python requirements (`fastapi`, `langgraph`, `litellm`) | 0 | 0 | 0 | 0 | **CLEAN / PASSED** |
| **OWASP ZAP** | Web API endpoints & Security Headers | 0 | 0 | 0 | 1 (Cookie SameSite) | **COMPLIANT** |

---

## 2. Key Findings, Policies, and Fixes

### A. Secret Detection (Gitleaks)
- **Zero Secrets in Repository**: No private RSA keys, production API tokens, or hardcoded passwords committed.
- **Key Management Policy**: RS256 private/public keypair loaded strictly via environment variables or ephemeral filesystem mount (`/certs`).

### B. Dependency Audits (pip-audit & govulncheck)
- Pinned secure releases: `pydantic>=2.0`, `pyjwt>=2.8.0`, `cryptography>=42.0.0`.
- Automated vulnerability scanning integrated in `.github/workflows/ci.yml`.

### C. Static Application Security Testing (Semgrep)
- Verified defenses against OWASP Top 10:
  - **SQL Injection**: All database queries parameterized via SQLAlchemy Core / asyncpg; ClickHouse mutations strictly sanitized with regex VIN validation.
  - **SSRF**: Outbound HTTP requests restricted to internal microservice mesh.
  - **Prompt Injection**: Pre-LLM safety guardrail intercepts dangerous instructions before model invocation.

### D. Multi-Tenant Data Protection & Isolation
- **Row-Level Security (RLS)**: Enforced in PostgreSQL on `tenant_id`.
- **Location Privacy**: Automated geohash truncation (`precision=5`, ~4.9 km) for non-manager roles (`viewer`).
- **Right to Erasure**: Hard delete mutation in ClickHouse + cache purge in Redis + audit trail entry in PostgreSQL.
