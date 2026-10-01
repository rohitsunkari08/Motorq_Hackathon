# SQL Optimisation Before/After Summary Table
Per NOTE.md §1.2, §5.3, §14: Demonstrating database engineering excellence with measured `EXPLAIN (ANALYZE, BUFFERS)` metrics on 100,000-vehicle dataset.

| Query ID | Workload Description | Engine | Optimization Technique | Before Execution Time | After Execution Time | Before I/O / Rows Scanned | After I/O / Rows Scanned | Speedup / Impact |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Q1** | Fleet Vehicle List + Latest SoH (`/fleets/{id}/vehicles`) | PostgreSQL 16 | Keyset Pagination (`vin > cursor`), Composite Index `(fleet_id, vin)`, Single Lateral JOIN (Zero ORM N+1) | **10.34 ms** (1 query + 50 secondary queries) | **2.97 ms** (single pass query) | 4,041 buffer pages hit/read + 50 extra network roundtrips | 244 buffer pages hit/read (1 query) | **3.48x latency speedup**, **16.5x I/O reduction**, eliminated N+1 connection churn |
| **Q2** | Open Fleet Alerts (`/alerts?status=open`) | PostgreSQL 16 | Partial Composite Index `ix_alert_open` on `alert(vin, raised_at DESC) WHERE resolved_at IS NULL` | **3.67 ms** | **1.78 ms** | 56 buffer pages + Top-N in-memory sort | 5 buffer pages + Bitmap index scan | **2.06x speedup**, **11.2x buffer I/O reduction**, index ignores 99%+ historical resolved alerts |
| **Q3** | 24-Hour Telemetry Aggregation (`/vehicles/{vin}/telemetry`) | ClickHouse 24.x | Materialised View Rollup (`telemetry_1m`) with `AggregatingMergeTree` vs Raw `telemetry` Scan | **77.25 ms** | **58.22 ms** | 288,000 rows read (12.4 MB compressed data) | 1,440 rows read (82 KiB data) | **1.33x latency speedup**, **200x fewer rows read**, **155x less disk I/O**, highly scalable under multi-user dashboard load |

---

### Detailed Plan Reports:
* [q1_before.txt](file:///c:/Documents/Motorq_Hackathon/docs/sql-writeup/q1_before.txt)
* [q1_after.txt](file:///c:/Documents/Motorq_Hackathon/docs/sql-writeup/q1_after.txt)
* [q2_before.txt](file:///c:/Documents/Motorq_Hackathon/docs/sql-writeup/q2_before.txt)
* [q2_after.txt](file:///c:/Documents/Motorq_Hackathon/docs/sql-writeup/q2_after.txt)
* [q3_before.txt](file:///c:/Documents/Motorq_Hackathon/docs/sql-writeup/q3_before.txt)
* [q3_after.txt](file:///c:/Documents/Motorq_Hackathon/docs/sql-writeup/q3_after.txt)
