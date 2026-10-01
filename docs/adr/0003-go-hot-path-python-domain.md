# ADR 0003: Go for Ingestion Hot-Path and Python for Domain API / ML / Agent

* **Status:** Accepted
* **Date:** 2026-09-30
* **Deciders:** Rohit (Platform Architecture)
* **Context:** High throughput requirement of 100,000+ events/sec on constrained hardware paired with rich domain logic, ML model inference, and LLM agent orchestration.

---

## 1. Context and Problem Statement
The platform has two distinct computational profiles:
1. **The Ingestion Hot Path:** High-volume, CPU- and I/O-intensive stream processing (Kafka consumption, JSON parsing, VIN check-digit validation, Bloom filter deduplication, ClickHouse batch insertion, sliding window alert evaluation) running at 100,000 to 300,000 ev/s.
2. **The Domain / AI Path:** Complex business workflows (FastAPI REST & SSE endpoints, dynamic programming optimization, XGBoost regression inference, pgvector semantic search, LangGraph agent tool calling, OAuth2/JWT RBAC).

---

## 2. Considered Options
* **Option 1: Polyglot Language Model** — Go for simulator & ingestion pipeline; Python for API, ML, and Copilot agent.
* **Option 2: Pure Python** — Python for both ingestion and API (using uvloop, multiprocessing, Faust/Kafka).
* **Option 3: Pure Go** — Go for everything, including REST API and ML/LLM services (using Go ML bindings).

---

## 3. Decision Outcome
**Chosen Option:** **Option 1: Go for Ingestion Hot Path + Python for Domain/ML/Agent**.

### Component Breakdown
* **Go (Simulator & Ingestion Service):**
  - Libraries: `franz-go` (zero-alloc Kafka client), `fastjson` (zero-alloc JSON parser), `clickhouse-go` (native TCP protocol batching), `go-redis`, `bits-and-blooms/bloom`, `mmcloughlin/geohash`, `prometheus/client_golang`.
  - Performance: Sustains 114,249 peak ev/s on a single machine with < 1.0 GB RAM and negligible GC pause.
* **Python (API, ML, Agent):**
  - Libraries: `FastAPI`, `SQLAlchemy/SQLModel`, `asyncpg`, `xgboost`, `scikit-learn`, `langgraph`, `litellm`, `sentence-transformers`.
  - Velocity: Rapid iteration on DP algorithms, Pydantic validation, ML training, and agentic workflows.

### Positive Consequences
* Solves the 100,000 ev/s throughput requirement on single developer laptop without multi-node clusters.
* Leverages Python's mature data science and LLM agent ecosystems.
* Clean separation of concerns between I/O stream workers and user-facing API servers.
