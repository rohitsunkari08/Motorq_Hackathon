# ADR 0002: Polyglot Storage Architecture (PostgreSQL + ClickHouse + Redis + pgvector)

* **Status:** Accepted
* **Date:** 2026-09-30
* **Deciders:** Rohit (Platform Architecture)
* **Context:** Balancing ACID transaction guarantees, ultra-high-throughput telemetry ingestion, sub-millisecond operational lookups, and semantic search.

---

## 1. Context and Problem Statement
Connected vehicle platforms manage fundamentally diverse data types:
1. **Relational Entities:** Fleets, vehicles, drivers, charging stations, tariffs, user accounts, and billing-grade charge plans requiring strict ACID semantics, foreign keys, and Row-Level Security (RLS).
2. **High-Frequency Time-Series Telemetry:** 100,000 events/sec generating 8.64 billion rows daily requiring petabyte-scale append performance, columnar compression, and analytical rollups.
3. **Operational Latest State:** Real-time dashboard queries needing vehicle location, current SoC, and rate-limiting counters in < 1 millisecond.
4. **Semantic Embeddings:** Knowledge base articles, battery degradation profiles, and vehicle cluster vectors for the Copilot AI assistant.

A single storage engine cannot satisfy all four requirements without severe compromises in performance, cost, or data consistency.

---

## 2. Considered Options
* **Option 1: Polyglot Tiering** — PostgreSQL 16 (3NF relational + pgvector), ClickHouse (columnar telemetry), and Redis 7 (operational KV store).
* **Option 2: Single Relational DB (PostgreSQL + TimescaleDB)** — Use PostgreSQL for everything.
* **Option 3: Document / Column-Family NoSQL (Cassandra / MongoDB)** — Use Cassandra or Mongo for telemetry.

---

## 3. Decision Outcome
**Chosen Option:** **Option 1: Polyglot Tiering**.

| Store | Role | CAP / PACELC Classification | Justification |
|---|---|---|---|
| **PostgreSQL 16** | Core business domain (Fleets, Vehicles, Chargers, Plans, Audit) | **CP** / PC-EC | ACID guarantees, Foreign Key integrity, Postgres Row-Level Security (RLS) for tenant isolation. |
| **pgvector** | AI Knowledge Base & Vehicle Degradation Embeddings | **CP** / PC-EC | Co-located with relational schema; eliminates separate vector DB infrastructure (Milvus/Pinecone). |
| **ClickHouse** | Canonical telemetry, 1-min rollups, daily statistics, charge sessions | **AP** / PA-EL | Inserts > 1M rows/s, 34 bytes/event ZSTD compression, ReplacingMergeTree deduplication, and O(1) partition drop. |
| **Redis 7** | Latest vehicle status (`veh:latest:{vin}`), rate-limit tokens | **AP** / PA-EL | In-memory sub-millisecond reads; atomic pipeline operations; transient loss is recoverable from telemetry stream. |

### Positive Consequences
* **Extreme Write Throughput:** ClickHouse absorbs 100,000+ ev/s easily while keeping disk footprint to ~34 bytes/event.
* **Rock-Solid Compliance:** Financial audit logs, charge plans, and user permissions reside in 3NF ACID Postgres.
* **Low Latency Reads:** Dashboard renders in < 2 seconds because latest vehicle positions are cached in Redis.
* **Unified AI Vectorization:** HNSW indexing on 384-dimensional embeddings runs natively within Postgres without distributed vector sync issues.

### Negative Consequences / Trade-offs
* Dual-write / CQRS complexity: Ingestion writes to ClickHouse and Redis simultaneously. Handled by making Redis an ephemeral cache and ClickHouse the durable source of truth.
