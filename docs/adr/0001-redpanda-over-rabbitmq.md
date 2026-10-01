# ADR 0001: Redpanda (Kafka API) Over RabbitMQ and Direct HTTP/MQTT

* **Status:** Accepted
* **Date:** 2026-09-30
* **Deciders:** Rohit (Platform Architecture)
* **Context:** Motorq Connected Vehicle Intelligence Hackathon — Real-time ingestion of 100,000+ ev/s across 100,000 vehicles with 3x bursts (300,000 ev/s).

---

## 1. Context and Problem Statement
Connected vehicles stream continuous telemetry (GPS, speed, battery state-of-charge, voltage, diagnostic trouble codes) at massive scales. To support 100,000 vehicles generating 100,000 events/sec with 3x bursts (up to 300,000 events/sec during shift starts), the platform requires a distributed message broker to act as the primary ingestion buffer and shock absorber.

The key requirements are:
1. **Partitioned Ordering:** Telemetry must be strictly sequenced per vehicle (`vin`) so state calculations (SoC drop, charging speed) are monotonic.
2. **Replayability:** In case downstream analytics or database sinks fall behind or fail, the platform must allow consumers to rewind offsets without data loss.
3. **Local & Cloud Agility:** Single-binary or minimal resource footprint on developer laptops (16 GB total RAM) while retaining cloud scalability.
4. **Standard Ecosystem:** Support for standard streaming protocols without custom broker lock-in.

---

## 2. Considered Options
* **Option 1: Redpanda (Kafka API compatible)** — C++ single-binary Raft-based broker implementing the Kafka protocol.
* **Option 2: Apache Kafka with ZooKeeper / KRaft** — The JVM-based industry standard streaming platform.
* **Option 3: RabbitMQ (AMQP)** — Traditional queue broker.
* **Option 4: Direct MQTT broker to backend** — Device-first IoT ingestion.

---

## 3. Decision Outcome
**Chosen Option:** **Option 1: Redpanda**.

### Positive Consequences
* **Protocol Compatibility:** Complete Kafka API compatibility allows standard client libraries (e.g., `franz-go` in Go) with zero vendor lock-in.
* **Deterministic Per-Vehicle Ordering:** Partitioning by key (`vin`) across 12 partitions guarantees strict per-vehicle ordering and parallel processing.
* **Lightweight Footprint:** Single C++ binary consumes < 1.5 GB RAM and 2 CPU cores locally (vs. JVM overhead of Kafka/ZooKeeper).
* **Replay & Retention:** Offsets can be replayed from any timestamp or offset, vital for handling ClickHouse sink downtime and disaster recovery.
* **Throughput:** Zero-copy architecture handles > 120,000 ev/s on a developer laptop without JVM garbage collection pauses.

### Negative Consequences / Risks
* Single-node configuration used in local development does not provide multi-node replication (addressed by deploying a 3-node Raft cluster in production Helm manifests).

---

## 4. Rejection Rationale
* **Apache Kafka + ZK/KRaft:** High memory baseline (~3-4 GB JVM heap) caused memory exhaustion on 16 GB developer machines alongside ClickHouse and Postgres.
* **RabbitMQ:** Lacks log-based replayability; messages are deleted once acknowledged by consumers. Routing queues by VIN would create thousands of unmanageable queues.
* **MQTT:** In our architecture, OEM clouds push batched HTTP/Kafka streams (Motorq model), rendering edge MQTT gateways unnecessary for cloud-to-cloud ingestion.
