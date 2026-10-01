# ADR 0004: At-Least-Once Delivery with Idempotent Sinks Over Distributed 2PC Transactions

* **Status:** Accepted
* **Date:** 2026-09-30
* **Deciders:** Rohit (Platform Architecture)
* **Context:** Guaranteeing data integrity and avoiding duplicate telemetry without sacrificing ingestion throughput.

---

## 1. Context and Problem Statement
In streaming systems processing vehicle telemetry, network blips, consumer restarts, or broker rebalances inevitably lead to duplicate events (~1–2% simulated retransmissions). The system must ensure that duplicate events do not corrupt analytical rollups, charging records, or odometer histories.

The platform requires an architecture that guarantees **effectively exactly-once semantics** across heterogeneous sinks (ClickHouse and Redis) under high load (100,000+ ev/s).

---

## 2. Considered Options
* **Option 1: At-Least-Once Delivery + Layered Idempotent Sinks** — Ingest commits Kafka offsets after processing; deduplicates via fast in-memory Bloom filter and relies on ClickHouse `ReplacingMergeTree` on `(vin, ts, seq)` as the authoritative deduplication engine.
* **Option 2: Kafka Exactly-Once Semantics (EOS / 2PC Transactions)** — End-to-end Kafka transactional producer and two-phase commit.
* **Option 3: Relational Upsert / Deduplication Table** — Check relational database before every write.

---

## 3. Decision Outcome
**Chosen Option:** **Option 1: At-Least-Once Delivery + Layered Idempotent Sinks**.

### Implementation Architecture
1. **In-Flight Deduplication (Bloom Filter):** A fast, per-partition in-memory Bloom filter (10M capacity, 0.1% false-positive rate) on `(vin, seq)` drops immediate duplicate bursts at wire speed.
2. **Authoritative Storage Deduplication (`ReplacingMergeTree`):** In ClickHouse, the primary telemetry table is configured with:
   ```sql
   ENGINE = ReplacingMergeTree(seq)
   PARTITION BY toYYYYMMDD(ts)
   ORDER BY (vin, ts, seq)
   ```
   Even if an offset rewind causes the same batch to be inserted twice, ClickHouse background merges deduplicate rows by the monotonic sequence number `seq`.
3. **Redis State Idempotency:** Redis `HSET veh:latest:{vin}` updates state using monotonic timestamp checks; out-of-order stale updates are ignored.

### Positive Consequences
* **Zero Transaction Overhead:** Avoids heavy distributed transaction coordinators (2PC), preserving 100k+ ev/s ingestion speed.
* **Disaster Recovery:** If the sink crashes, consumer group rebalance simply replays uncommitted messages without risk of duplicate phantom records.
* **Verified in Chaos Testing:** During simulated container kills (`docker kill redpanda` and `docker kill ingest-sink`), 100% of generated unique events matched database rows with 0 duplicate inflation.
