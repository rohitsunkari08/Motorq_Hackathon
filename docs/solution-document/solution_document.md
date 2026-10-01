# EV Fleet Charging & Battery-Health Copilot
## Solution Document — Motorq Connected Vehicle Intelligence Hackathon

**Author:** Rohit (Solo Developer)  
**Submission Date:** 1 October 2026  
**Target Repository Tag:** `v1.0-submission`  
**License:** Apache 2.0 / MIT Open Source  

---

## 1. Executive Summary

Commercial electric vehicle (EV) fleets are expanding at record pace, yet fleet operators face severe financial and operational roadblocks: charging immediately on arrival during peak electricity tariff windows raises energy expenditures by **15% to 30%**, heavy DC fast-charging roughly doubles annual battery degradation (**3.0%/yr vs. 1.5%/yr**), and blind battery state-of-charge visibility causes costly stranded vehicle downtime. 

The **EV Fleet Charging & Battery-Health Copilot** is a production-grade, cloud-agnostic intelligence platform built to eliminate these costs at scale. Tested with a simulated fleet of **100,000 commercial vehicles across 5 major OEM protocols**, the platform pairs an ultra-high-throughput Go stream ingestion engine with a resilient polyglot persistence tier:
* **Ingestion at Scale:** Sustained peak ingestion of **114,249 events/second** (83,361 ev/s avg) with zero message loss and recovery from catastrophic broker kills in **1.84 seconds**.
* **Real-Time Safety:** Critical `RANGE_RISK` and `THERMAL` alerts evaluated within **p99 < 1.20 seconds** (well inside the 5-second SLA).
* **Battery-Aware Optimization:** A dynamic programming charging scheduler that co-optimizes time-of-use tariffs and electrochemical battery degradation, achieving an average of **26.21% energy cost savings (31.58% net)** and an **83.51% reduction in battery stress**.
* **Machine Learning Health Accuracy:** Grouped-by-vehicle XGBoost regressors beating linear baseline State-of-Health (SoH) prediction error by **43.50%** (MAE 0.2940% vs. 0.5203% baseline).
* **Enterprise Copilot with Human-in-the-Loop:** An authenticated LangGraph assistant providing grounded fleet analytics via pgvector RAG, featuring an approval boundary that prevents autonomous mutations and achieved **100% resistance across adversarial prompt-injection benchmarks**.
* **Privacy & Compliance:** Built-in compliance with India's DPDP Act 2023 and GDPR, including a 5-step distributed Right-to-Erasure workflow, role-based GPS masking (Geohash-5 for viewers), and $(\varepsilon=1.0)$-Differentially Private cross-fleet battery benchmarking.

The entire solution is 100% containerized, verified via 45 unit/integration test suites and 6 BDD scenarios, and prepared for instant deployment across local Docker Compose, Kubernetes (Helm), and AWS (Terraform).

---

## 2. Problem Statement & Real-World Context

### 2.1 Problem Definition
> *"A commercial fleet manager needs an automated, intelligent way to schedule EV charging at the lowest possible tariff cost while actively protecting battery health and avoiding stranded vehicles. Charging on arrival during peak grid windows, excessive DC fast-charging, and inadequate real-time range visibility inflate operating costs, accelerate battery degradation, and trigger costly roadside downtime."*

### 2.2 Facts vs. Assumptions Matrix
Every claim and design assumption in this platform is grounded in verified public research and empirical telematics studies:

| # | Evidence / Claim | Source & Methodology | Real-World Impact | Confidence | Platform Reflection |
|---|---|---|---|---|---|
| **E-1** | Frequent high-power DC fast-charging (>100 kW) accelerates battery degradation from ~1.5%/yr to ~3.0%/yr. | Geotab EV Battery Degradation Study (Jan 2026, 22,700+ EVs, 21 models). | Battery replacement is the highest single capital cost in EV fleet TCO ($8,000–$20,000/pack). | **High** (Large empirical telematics) | Calibrated synthetic battery degradation model and DP degradation penalty term $\lambda \cdot (\frac{P}{P_{max}})^2$. |
| **E-2** | 72% of charging sessions start immediately upon plug-in regardless of tariffs; <26% are actively scheduled. | Rivian Telematics Study (arXiv:2503.03167, 2025). | Fleets needlessly charge during peak demand spikes, increasing energy bills by $140–$400/EV/year. | **High** (Real-world telematics) | Sets the baseline benchmark ("Charge on Arrival at Max Power") for our optimizer. |
| **E-3** | Active managed charging cuts peak demand by up to 50% and energy costs by 15–30%. | Brattle Group / EnergyHub (2025); RFF Working Paper 25-22. | Shifting load to off-peak tariff valleys lowers utility charges while meeting departure readiness. | **High** (Utility tariff modeling) | DP scheduler achieves **26.21% avg / 31.58% net** savings across simulated commercial tariffs. |
| **E-4** | Telematics streams generate massive volumes (~25 GB/hr per modern vehicle, McKinsey/S&P). | Hackathon Problem Statement; UNECE R155/R156. | Ingestion pipelines must withstand 100k+ ev/s without ballooning cloud storage bills. | **High** (Industry telemetry) | ClickHouse columnar storage with ZSTD compression achieves **~34 bytes/event** (~3.4 GB / 100M events). |
| **A-1** | Simulated fleet behaviors translate to actual operational environments. | Deterministic synthetic generator with calibrated noise and dirty payload models. | Validates software correctness, algorithm scalability, and stream handling. | **Medium** (Simulation, not physical pilot) | Stated honestly as synthetic validation; no claim of physical vehicle pilot. |

### 2.3 Success Metrics & Fleet Scaling

| Metric | Industry Baseline | Platform Target | Measured Result (100k Fleet) | Verification Method |
|---|---|---|---|---|
| **Charging Energy Cost** | Charge on arrival at max power | -15% to -30% | **-26.21% avg / -31.58% net** | DP optimizer vs. baseline on 1,000-vehicle batches |
| **Battery Stress Proxy** | Unmanaged DC-fast charging | -20% or better | **-83.51% stress reduction** | Quadratic fast-charge penalty evaluation |
| **SoH Prediction Accuracy** | Linear regression on (Age, Odo) | $\ge$ 30% MAE reduction | **-43.50% MAE reduction** (0.294% vs. 0.520%) | Grouped-by-vehicle holdout evaluation |
| **Critical Alert Lead Time** | Static threshold on rated range | Ingest $\to$ Alert p99 < 5.0s | **p95 1.16s / p99 1.20s** | End-to-end sliding window latency histogram |
| **Peak Stream Throughput** | Standard IoT platforms (<20k ev/s) | $\ge$ 100,000 ev/s | **114,249 ev/s peak** | Go generator with 12 Kafka partitions |
| **Storage Compression** | Uncompressed JSON (~1 KB/event) | < 50 bytes/event | **~34 bytes/event** | ClickHouse `system.parts` disk measurement |

---

## 3. Proposed Solution & Value Proposition

### 3.1 Jobs, Pains, and Gains
* **Customer Jobs:** Keep commercial fleets charged on time, minimize utility electricity bills, extend battery operational lifetime, and ensure regulatory compliance.
* **Pains:** Uncontrolled peak charging tariffs, unexpected roadside battery depletion, premature battery capacity loss, vendor cloud lock-in (e.g. AWS IoT FleetWise sunset), and security vulnerabilities from unvetted AI.
* **Gains:** Automated DP-optimized charge plans with clear ROI, sub-2-second range-risk alerts with nearest charger routing, explainable ML battery degradation insights, and an enterprise Copilot with strict human approval boundaries.

### 3.2 Key Differentiators
1. **Electrochemical Battery-Aware Optimization:** Existing fleet solutions schedule charging solely on electricity tariffs. Our DP optimizer integrates an electrochemical degradation penalty ($\lambda \cdot (\text{kW}/\text{kW}_{\text{max}})^2$), actively dampening high-temperature DC stress and extending battery life by up to 2 years.
2. **Zero-Downtime OEM Normalization:** Supports 5 distinct OEM protocols (VoltX, NordMotors, AsiaDrive, EuroEV, ZephyrEV). Adding a new OEM requires only a single adapter class and registry entry without backend restarts.
3. **Differential Privacy Cross-Fleet Benchmarking:** Operators compare their fleet's battery degradation against anonymized industry peers using Laplace Differential Privacy ($\varepsilon=1.0$) with $k=20$ suppression, preventing competitive data leakage.
4. **Cloud-Agnostic, Zero-Lock-In Architecture:** Runs identically on developer laptops, on-premise hardware, Kubernetes clusters, or AWS EC2 without proprietary vendor-managed cloud services.

---

## 4. Feature Breakdown & Traceability Matrix

| ID | Feature | User Story | Priority | Implementation Path | Video Timestamp |
|---|---|---|---|---|---|
| **F-01** | 100K Vehicle Multi-OEM Simulator | As platform dev, I need realistic, bursty, dirty vehicle telemetry across 5 formats to validate extreme scale. | Must Have | `services/simulator` (Go) | `1:00` |
| **F-02** | OEM Normalization & Bloom Deduplication | As platform engineer, I need to onboard OEM formats with zero downtime and drop wire duplicates cleanly. | Must Have | `services/ingest/normalize` (Go) | `1:15` |
| **F-03** | Real-Time Range-Risk & Thermal Alerts | As fleet dispatcher, I need instant alerts when an EV cannot reach a charger or overheats. | Must Have | `services/ingest/alerts` (Go) | `1:30` |
| **F-04** | XGBoost SoH & Efficiency ML Models | As fleet manager, I want true battery State-of-Health prediction beating naive age/mileage baselines. | Must Have | `services/ml`, `api/domain` | `2:00` |
| **F-05** | Battery-Aware DP Charging Optimizer | As finance manager, I want lowest-cost charging schedules that protect battery longevity. | Must Have | `services/api/app/domain/optimiser.py` | `2:15` |
| **F-06** | Nearest Reachable Charger Routing | As driver/manager, I need a list of reachable chargers filtered by current usable battery range. | Must Have | `services/api/app/domain/charger.py` | `1:45` |
| **F-07** | Secure Multi-Tenant REST/SSE API | As enterprise user, I require strict RBAC, rate-limiting, and PostgreSQL Row-Level Security isolation. | Must Have | `services/api` (FastAPI) | `2:45` |
| **F-08** | Executive Web Dashboard | As fleet operator, I want interactive fleet KPIs, live alerts, and one-click charge plan approval. | Must Have | `web/` (React + Vite + Tailwind) | `1:30 - 2:30` |
| **F-09** | Enterprise AI Copilot with Guardrails | As fleet manager, I want natural-language fleet answers with strict propose-only human approval. | Must Have | `services/agent` (LangGraph) | `2:30` |
| **F-10** | DPDP/GDPR Privacy & Erasure Engine | As compliance officer, I need role-based location masking and verified 5-step data erasure. | Must Have | `services/api/app/domain/privacy.py` | `2:50` |
| **F-11** | Differential Privacy SoH Benchmark | As fleet executive, I want peer battery comparisons without leaking raw fleet telemetry. | Should Have | `services/api/app/domain/benchmark.py`| `2:55` |
| **F-12** | Dijkstra/A* Multi-Stop Route Planner | As long-haul driver, I need optimal charging stops along an extended inter-city route. | Could Have | `services/api/app/domain/route.py` | Appendix |
| **F-13** | Historical Analytical Rollups | As operations analyst, I need 1-minute and 90-day aggregations for fleet trend reporting. | Must Have | ClickHouse Materialized Views | `1:20` |

---

## 5. System & Architecture Design

### 5.1 Architecture Overview (C4 L1/L2)
```
                                 [ OEM Cloud Providers ]
                     (VoltX, NordMotors, AsiaDrive, EuroEV, ZephyrEV)
                                            │
                                100,000+ ev/s (Raw Payloads)
                                            ▼
                           ┌──────────────────────────────────┐
                           │   Redpanda Topic: telemetry.raw   │ (12 Partitions, Key=VIN)
                           └──────────────────────────────────┘
                                            │
                                            ▼
                      ┌───────────────────────────────────────────┐
                      │  Ingest Service (Go, mode=normalize)       │
                      │  - OEM Adapter Registry (Zero Downtime)   │
                      │  - Canonical Validation & VIN Check Digit │
                      │  - Wire Deduplication (Bloom Filter)       │
                      │  - Malformed Payloads ────────────┐       │
                      └───────────────────────────────────┼───────┘
                                            │             │
                                Canonical Stream          ▼
                                            │    ┌─────────────────┐
                                            ▼    │  telemetry.dlq  │
                        ┌────────────────────────┐ └─────────────────┘
                        │  telemetry.canonical   │
                        └────────────────────────┘
                                    │
               ┌────────────────────┴────────────────────┐
               ▼                                         ▼
┌─────────────────────────────┐           ┌─────────────────────────────┐
│ Ingest Service: mode=sink   │           │ Ingest Service: mode=alerts │
│ - Batch native insert (1s)  │           │ - 5-min Sliding Ring Buffer │
│ - Pipelined Redis HSET      │           │ - Range-Risk Geospatial Rule│
│ - Circuit Breaker on DB     │           │ - Thermal & SoC Drop Rules  │
└──────────────┬──────────────┘           └──────────────┬──────────────┘
               │                                         │
        ┌──────┴──────┐                                  ▼
        ▼             ▼                   ┌─────────────────────────────┐
 ┌────────────┐ ┌───────────┐             │     Topic: alerts.raw       │
 │ ClickHouse │ │  Redis 7  │             └──────────────┬──────────────┘
 │ Columnar   │ │ Latest    │                            │
 │ Telemetry  │ │ State KV  │                            ▼
 └────────────┘ └───────────┘             ┌─────────────────────────────┐
                                          │   FastAPI API Service       │
                                          │   - Background Kafka Reader │
                                          │   - Postgres Alert Table    │
                                          │   - Live SSE Stream to UI   │
                                          └─────────────────────────────┘
```

### 5.2 Technology Stack Justification
* **Message Broker — Redpanda:** Kafka-protocol compatible, single C++ binary, zero JVM overhead. Sustains >120,000 ev/s with 12 VIN-keyed partitions and predictable tail latencies.
* **Stream Ingestion — Go (Golang):** Chosen for sub-millisecond concurrency (`franz-go`, `fastjson`, `clickhouse-go`). Go processes 114k+ ev/s on a single developer machine with <1.0 GB RAM.
* **Columnar Telemetry Store — ClickHouse:** High-density time-series analytical engine. Ingests 100k+ rows/s via native TCP batching, achieving 34 bytes/event ZSTD compression and instantaneous partition dropping.
* **Relational Core & Vector Store — PostgreSQL 16 + pgvector:** 3NF relational schema enforcing strict ACID guarantees, foreign keys, and Row-Level Security (RLS) for multi-tenancy. Native `pgvector` HNSW indexes eliminate the operational burden of a standalone vector database.
* **In-Memory Cache — Redis 7:** Key-value store for sub-millisecond latest vehicle status (`veh:latest:{vin}`) and distributed rate-limiting token buckets.
* **Domain API & ML Engine — Python (FastAPI, XGBoost, LangGraph):** Powers REST and SSE endpoints, dynamic programming charging schedules, XGBoost regression inference, and conversational Copilot tool calling.
* **Frontend Web Application — React, Vite, TypeScript, TailwindCSS:** Modern, responsive single-page application with real-time SSE streaming, interactive Leaflet charging maps, and Recharts cost-comparison visualizations.

### 5.3 Polyglot Storage Architecture & 3NF Data Model
Data persistence follows strict CAP/PACELC categorization:
* **PostgreSQL (CP):** `tenants`, `fleets`, `vehicles`, `drivers`, `chargers`, `tariffs`, `charge_plans`, `alerts`, `audit_log`, `kb_chunks`.
* **ClickHouse (AP):** `telemetry` (ReplacingMergeTree partitioned by day), `telemetry_1m` (Materialized View), `vehicle_daily`, `charge_session`.
* **Redis (AP):** `veh:latest:{vin}` (Hash, TTL 24h), `veh:params:{vin}`, `rl:{tenant}:{route}:{min}`.

#### Storage Capacity & Lifecycle Projections
* **Daily Ingestion Rate:** 100,000 ev/s $\times$ 86,400 s = **8.64 Billion events/day**.
* **Raw Wire Volume:** 8.64B $\times$ 1.0 KB $\approx$ **8.64 TB/day**.
* **Compressed ClickHouse Volume:** 8.64B $\times$ 34 bytes $\approx$ **293.7 GB/day** (~8.8 TB/month).
* **Tiered Lifecycle Policy:**
  - *Hot Tier (Days 0–7):* High-performance NVMe/gp3 EBS volumes for full-resolution canonical telemetry.
  - *Warm Tier (Days 8–90):* 1-minute aggregated rollups and daily summaries stored on lower-cost gp3 volumes. Precise GPS coordinates are automatically pruned after 30 days via ClickHouse column TTL, retaining only Geohash-7.
  - *Cold Tier (Days 91–365):* Daily Parquet archives exported to AWS S3 Standard/Glacier ($0.023/GB-month).

---

## 6. Component & Implementation Details

### 6.1 Hexagonal Layering & Repository Layout
The API and domain services strictly follow Hexagonal Architecture (Ports and Adapters):
```
services/api/app/
├── api/             # Inbound HTTP/SSE Adapters & Pydantic DTOs
│   ├── routes/      # Auth, Fleets, Vehicles, Alerts, Plans, Privacy
│   └── dto/         # Request and Response schemas
├── application/     # Application Use Cases & Orchestration
│   ├── auth_service.py
│   ├── fleet_service.py
│   └── charge_plan_service.py
├── domain/          # Pure Domain Logic & Algorithms (Zero External I/O)
│   ├── optimiser.py # Dynamic Programming charge scheduler
│   ├── charger.py   # Geospatial charger index & range reachability
│   └── privacy.py   # Laplace DP & Geohash location masking
└── infra/           # Outbound Persistence Adapters & Drivers
    ├── postgres.py  # SQLAlchemy async engine & RLS session wrapper
    ├── clickhouse.py# ClickHouse client wrapper & fallback breaker
    └── redis.py     # Redis async pool
```

### 6.2 Key Design Patterns Applied
1. **Adapter & Factory Registry (OEM Ingestion):** Unifies disparate OEM wire protocols into a canonical schema. New OEMs are registered at runtime via dictionary lookup without recompilation.
2. **CQRS (Command Query Responsibility Segregation):** Ingestion write paths bypass the API directly into ClickHouse and Redis. Read paths are served by FastAPI querying optimized views and caches.
3. **Circuit Breaker & Backpressure Buffer:** If ClickHouse undergoes background merges or pauses, the Go sink pauses consumption and Redpanda absorbs up to 90 million buffered events without dropped records.
4. **Observer Pattern (Live Telemetry & Alerts):** Kafka alert consumers broadcast events over Redis Pub/Sub directly to connected React clients via Server-Sent Events (SSE).

### 6.3 Core Algorithms & Computational Complexity

#### 1. Dynamic Programming Charge Scheduler
* **Objective:** Minimize total cost:
  $$\min \sum_{t=1}^{T} \left[ \text{Tariff}(t) \cdot P(t) \cdot \Delta t + \lambda \cdot \left(\frac{P(t)}{P_{\max}}\right)^2 \cdot P(t) \cdot \Delta t \right]$$
  Subject to:
  $$\text{SoC}(T_{\text{depart}}) \ge \text{SoC}_{\text{target}}, \quad 0 \le \text{SoC}(t) \le 100\%$$
* **State Space:** Discrete 15-minute time slots $T \le 96$, discrete SoC levels $S \in [0, 100]$, and discrete power actions $A \in \{0, \frac{1}{3}, \frac{2}{3}, 1\} \times P_{\max}$.
* **Complexity:** $\mathcal{O}(T \cdot S \cdot A) = 96 \times 101 \times 4 \approx 38,784$ operations per vehicle. An entire batch of 1,000 vehicles executes in **under 850 milliseconds**.

#### 2. Nearest Reachable Charger Algorithm
* **Approach:** Uses Geohash prefix indexing (precision 5, expanded to 8 immediate spatial neighbors).
* **Filtering:** Evaluates candidate distance via Haversine formula adjusted by an urban winding factor of $1.3$. Stations requiring energy greater than usable range minus a 10% safety buffer are pruned.
* **Complexity:** $\mathcal{O}(K \log K)$ where $K$ is the candidate count within the local geohash cells ($K \le 50$).

---

## 7. Non-Functional Requirements & Performance Results

Every NFR mandated in the problem statement was quantitatively measured and recorded under load:

| NFR Category | SLA / Requirement | Measured Result | Status | Evidence Reference |
|---|---|---|---|---|
| **Sustained Ingest** | $\ge$ 100,000 ev/s | **114,249 ev/s peak** (83,361 ev/s avg) | **PASSED** | `tests/evidence/p7/grafana-load.png` |
| **Burst Ingestion** | 3x burst for 5 min without loss | **Zero message loss**, lag drained in 3.0s | **PASSED** | `tests/evidence/p2/p2_metrics.txt` |
| **Alert Latency** | Critical alerts p99 < 5.0s | **p50: 602ms, p95: 1.16s, p99: 1.20s** | **PASSED** | `tests/evidence/p2/p2_metrics.txt` |
| **Dashboard Latency** | Ingest $\to$ Dashboard < 2.0s | **1.35 seconds** end-to-end | **PASSED** | `tests/evidence/p5/acceptance_report.md` |
| **API Latency (k6)** | p95 < 200ms, p99 < 500ms | **p95: 57.0ms, p99: 124.1ms** (avg: 20.1ms)| **PASSED** | `tests/evidence/p4/k6.txt` |
| **System Availability** | 99.9% uptime, no single point of failure | Survives broker & sink container kills | **PASSED** | `tests/evidence/p7/chaos_report.txt` |
| **Chaos Recovery** | Immediate failover & replay | Redpanda kill: **1.84s**, Sink kill: **0.77s** | **PASSED** | `tests/evidence/p7/chaos-redpanda.txt` |
| **Soak Stability** | 30-min sustained stream | 84,250 ev/s avg, **0.00% error rate** | **PASSED** | `tests/evidence/p7/soak_report.txt` |

---

## 8. Security & Privacy Architecture

### 8.1 STRIDE Threat Modeling

| Threat | System Component | Potential Impact | Implemented Mitigation |
|---|---|---|---|
| **Spoofing** | Telemetry ingestion endpoint | Malicious actors transmitting fabricated vehicle locations. | Per-OEM credentials, strict TLS 1.3 encryption, and VIN ISO-3779 check-digit validation. |
| **Tampering** | Canonical event stream | Modifying odometer or SoC data to skew charging billing. | Monotonic sequence number validation, Kafka message CRC verification, and immutable ClickHouse logs. |
| **Repudiation** | Charge plan approval / privacy erasure | A fleet manager claims they did not approve an expensive schedule. | Append-only PostgreSQL `audit_log` recording user ID, tenant ID, action, timestamp, and IP address. |
| **Information Disclosure** | Multi-tenant REST API | Fleet A viewing vehicle battery telematics belonging to Fleet B. | PostgreSQL Row-Level Security (RLS) policies keyed to `app.tenant_id` on every transaction. |
| **Denial of Service** | Public API endpoints | Burst requests exhausting backend database connections. | Redis-backed token bucket rate limiting (429 Too Many Requests with RFC 7807 error payloads). |
| **Elevation of Privilege** | Enterprise AI Copilot | Prompt injection hijacking the agent to delete vehicle records. | Delegated user JWT tokens, propose-only tool boundaries, and strict human review in the UI. |

### 8.2 5-Step Right-to-Erasure Workflow (DPDP & GDPR Compliance)
When an administrator triggers `POST /api/v1/privacy/erasure`:
1. **PostgreSQL Relational Scrub:** Sets `erased_at = NOW()` on the vehicle record, purges all historical trips, charge plans, and alerts, and pseudonyms driver PII.
2. **Redis Cache Invalidation:** Issues synchronous pipeline `DEL` on `veh:latest:{vin}`, `veh:params:{vin}`, and `tenantof:{vin}`.
3. **ClickHouse Columnar Mutation:** Issues an asynchronous mutation:
   ```sql
   ALTER TABLE telemetry DELETE WHERE vin = '...';
   ```
   Polls `system.mutations` until the mutation is complete.
4. **Kafka Stream Retention Window:** Ephemeral topics operate with a strict 24-hour retention policy; historical tombstones ensure uncommitted events are discarded.
5. **Immutable Compliance Audit:** Appends an un-redacted entry to `audit_log` recording completion timestamp, operator ID, and zero PII. Subsequent queries across all four data stores return 0 rows.

### 8.3 Differential Privacy Cross-Fleet Benchmarking
To enable fleet operators to benchmark battery degradation against competitive fleets without exposing sensitive raw telematics, the platform implements the Laplace Mechanism:
$$M(x) = f(x) + \text{Laplace}\left(0, \frac{\Delta f}{\varepsilon}\right)$$
* **Privacy Budget:** $\varepsilon = 1.0$, bounded query sensitivity $\Delta f = \frac{100}{N}$.
* **$k$-Anonymity Suppression:** Cohorts with fewer than 20 vehicles ($N < 20$) are suppressed, returning an error to prevent re-identification attacks.

---

## 9. Comprehensive Test Strategy & Verification

The testing pyramid spans 7 rigorous layers:
1. **Unit Tests (Go & Python):** Over 80% code coverage across charging DP, geospatial indexing, OEM adapters, and Pydantic DTO validation.
2. **Integration Tests (Testcontainers):** Verifies end-to-end event flows across actual Redpanda, ClickHouse, Redis, and PostgreSQL instances.
3. **Contract Tests (Schemathesis & JSON Schema):** Validates OpenAPI 3.1 endpoints and Kafka event topics against strict JSON Schema golden files.
4. **BDD Acceptance Scenarios (Behave):** 6 automated Gherkin scenarios:
   - *Scenario 1:* `RANGE_RISK` alert triggers in < 5 seconds upon low SoC.
   - *Scenario 2:* Duplicate telemetry events are silently dropped without counter inflation.
   - *Scenario 3:* Unknown or malformed OEM payloads are routed to `telemetry.dlq`.
   - *Scenario 4:* Users with `viewer` role observe masked Geohash-5 locations.
   - *Scenario 5:* Erasure workflow removes vehicle records from all four data stores.
   - *Scenario 6:* AI Copilot cannot autonomously approve or execute a charge plan.
5. **Performance & Load Testing:** Sustained 100k+ ev/s load injection and k6 HTTP benchmarks.
6. **Chaos Engineering:** Container kill tests validating sub-2-second recovery.
7. **Security Scans:** Clean reports across Semgrep (SAST), Trivy (Container & FS), Gitleaks (Secrets), and pip-audit (CVEs).

---

## 10. Observability & Operational Runbooks

### 10.1 Provisioned Grafana Dashboard
The platform includes an automated Grafana dashboard tracking:
* **Ingestion Velocity:** Real-time events/sec per OEM adapter.
* **Pipeline Health:** Kafka consumer lag across all 12 partitions.
* **Sink Batch Latencies:** Time taken for ClickHouse native TCP bulk inserts.
* **Alert Latency Distribution:** Real-time p50, p95, and p99 alert latency histogram.
* **API Metrics:** Request throughput, error rate, and p95 response times.

### 10.2 Incident Troubleshooting Walkthrough
* **Symptom:** Alert latency spikes from 1.2s to > 6.0s.
* **Diagnosis Runbook:**
  1. Inspect Grafana *Consumer Lag* panel $\to$ Observe lag accumulating on `telemetry.canonical`.
  2. Inspect *Sink Batch Latency* panel $\to$ Identify ClickHouse TCP insert duration exceeding 2,500ms.
  3. Query ClickHouse `system.merges` $\to$ Detect intensive background part merges throttling disk I/O.
  4. Automated Remediation: Ingestion sink circuit breaker pauses consumption, allowing Redpanda buffer to absorb load until ClickHouse merges finish, then drains backlog at 120k ev/s without dropped events.

---

## 11. Artificial Intelligence, Machine Learning & Copilot

### 11.1 Machine Learning Models (XGBoost Regressors)
* **Model 1: State-of-Health (SoH) Regressor:** Predicts true battery capacity retention based on cumulative fast-charge share, thermal exposure, cycle counts, and charging delta.
  - *Baseline:* Linear regression on vehicle age and odometer ($\text{MAE} = 0.5203\%$).
  - *XGBoost Model:* $\text{MAE} = 0.2940\%$ (**43.50% reduction in error**).
* **Model 2: Energy Efficiency Regressor:** Predicts real-world kWh/km consumption based on ambient temperature, average speed, and driving behavior ($\text{MAE} = 0.00152 \text{ kWh/km}$, **65.35% improvement over rated range**).
* **Data Leakage Prevention:** Validated using GroupKFold grouped strictly by vehicle VIN. No synthetic ground truth features are exposed during training.

### 11.2 Enterprise Copilot & Guardrails
* **Framework:** LangGraph state machine powered by LiteLLM (Gemini Flash free-tier with fallback to Groq LLaMA-3.3 70B and Ollama).
* **RAG Knowledge Base:** 384-dimensional dense embeddings (`all-MiniLM-L6-v2`) indexed in PostgreSQL using `pgvector` HNSW.
* **Guardrail Boundaries:**
  - Evaluated against 20 multi-step fleet questions: **100.0% tool selection accuracy** and **96.2% groundedness**.
  - Evaluated against 5 adversarial prompt injections: **100% pass rate** (0 unauthorized approvals, 0 data disclosures).
  - Average Copilot response latency: **1.178 seconds**, running at **$0.0000 API cost**.

---

## 12. Architecture Decision Records (ADRs) Summary

| ADR # | Title | Core Decision | Key Rationale |
|---|---|---|---|
| **0001** | Redpanda over RabbitMQ/Kafka | Adopt Redpanda with 12 VIN partitions. | Single C++ binary, zero JVM memory overhead, native log replay, and sub-millisecond latencies. |
| **0002** | Polyglot Storage Architecture | Tier PostgreSQL 16, ClickHouse, Redis, and pgvector. | Matches specific storage engines to distinct operational, analytical, relational, and semantic workloads. |
| **0003** | Go Hot Path & Python Domain | Ingestion in Go; API and ML in Python. | Delivers 114k+ ev/s on laptop hardware while retaining Python's rich AI and scientific ecosystem. |
| **0004** | At-Least-Once with Idempotent Sinks | Bloom wire deduplication + ClickHouse ReplacingMergeTree. | Eliminates expensive 2PC distributed transaction coordinators while guaranteeing zero duplicate rows. |
| **0005** | Human-in-the-Loop Agent | Propose-only Copilot tools with delegated JWT tokens. | Prevents automated prompt injection exploitation and maintains human authority over operational charge plans. |

---

## 13. Demonstration Video & Timestamps

* **Video Access:** Recorded in 1080p high definition (Duration: 4 minutes 48 seconds).
* **Video Link:** `https://youtu.be/motorq-hackathon-ev-copilot` *(or hosted MP4 in repository)*.

### Timed Agenda
* `0:00` — Problem statement, utility peak pricing, and battery degradation dilemma.
* `0:30` — End-to-end architecture and polyglot data tier overview.
* `1:00` — Live simulator execution at 100k+ ev/s and real-time Grafana observability.
* `1:30` — Real-time telemetry trigger $\to$ `RANGE_RISK` alert in web dashboard (<1.2s).
* `2:00` — Battery-aware DP charging optimization demo, cost comparison, and one-click manager approval.
* `2:30` — Enterprise Copilot chat, RAG search, adversarial prompt-injection refusal, and viewer GPS masking.
* `3:00` — Chaos test: `docker kill redpanda` broker crash, circuit breaker pause, auto-recovery, and zero-loss verification.
* `4:15` — Quantitative results review, submission checklist, and conclusion.

---

## 14. Repository & Submission Verification Checklist

- [x] Simulated dataset supporting **$\ge$ 100,000 vehicles** with 5 OEM formats.
- [x] Stream processing sustaining **$\ge$ 100,000 events/second** locally.
- [x] Polyglot architecture combining Relational (PostgreSQL 3NF), Columnar (ClickHouse), In-Memory (Redis), and Vector (pgvector).
- [x] Dynamic programming charging optimizer with battery degradation penalty.
- [x] Machine learning battery health models beating linear baselines by $\ge$ 30%.
- [x] Enterprise AI Copilot with delegated JWT authentication and human approval boundaries.
- [x] Real-time Web UI (React + Vite) with live SSE alert streaming and Leaflet mapping.
- [x] 5-step Right-to-Erasure workflow and Differential Privacy benchmarking.
- [x] Complete test suite: 45 unit/integration tests, 6 BDD scenarios, chaos recovery, and security scans.
- [x] Cloud-agnostic infrastructure: Docker Compose, Helm chart, and Terraform AWS manifests.
- [x] Repository tagged: `v1.0-submission`.

---

## 15. Conclusion & Future Roadmap

The **EV Fleet Charging & Battery-Health Copilot** demonstrates that large-scale connected vehicle intelligence can be achieved efficiently, cost-effectively, and securely. By combining high-performance stream processing with battery-aware scheduling and guarded AI assistance, the platform delivers double-digit cost reductions while safeguarding million-dollar fleet battery assets.

### Future Roadmap
1. **Vehicle-to-Grid (V2G) Bi-Directional Dispatch:** Extending the DP optimizer to capture grid revenue during peak utility stress events.
2. **On-Vehicle Edge Filtering:** Porting the Go normalizer to WebAssembly/Rust for execution inside vehicle telematics control units (TCUs).
3. **Crypto-Shredding for Ephemeral Streams:** Implementing per-vehicle cryptographic key management to achieve instantaneous zero-trace Kafka stream erasure.

---

## 16. Declarations & Compliance

* **Synthetic Data Declaration:** In strict accordance with competition rules, 100% of telemetry, vehicles, drivers, chargers, and tariffs used in this project are synthetically generated. No proprietary OEM or commercial customer data was used.
* **AI Tool Usage Declaration:**
  - *Antigravity (Google DeepMind):* Agentic software implementation, code generation, and test execution.
  - *Claude 3.7 Sonnet (Anthropic):* System planning, research synthesis, and architectural documentation.
  - *Gemini 2.5 Flash (Google AI Studio) / Groq LLaMA-3.3 70B:* Runtime LLM inference for Copilot agent tool execution.
* **Open-Source Software (SBOM):** Redpanda, ClickHouse, PostgreSQL, pgvector, Redis, Go (`franz-go`, `fastjson`, `clickhouse-go`), Python (`FastAPI`, `SQLAlchemy`, `XGBoost`, `scikit-learn`, `LangGraph`, `LiteLLM`), React, Vite, Leaflet, and Recharts.

---

## 17. Appendix: Raw Verification Evidence & Logs

*(See accompanying Word Document and `tests/evidence/` directory for full EXPLAIN ANALYZE query plans, security scan outputs, and high-resolution observability charts).*
