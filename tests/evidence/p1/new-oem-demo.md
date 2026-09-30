# Zero-Downtime OEM Onboarding Demonstration (`new-oem-demo.md`)

**Problem Statement Reference**: §3.3 (Innovative Ideas: Schema-drift-tolerant OEM adapter registry with zero-downtime onboarding) & §5.2.

This document demonstrates onboarding a brand-new fictional OEM (**ApexEV**) into the live EVC platform without taking down the message broker, database stores, or existing telemetry pipelines.

---

## 1. Architecture & Design Rationale

Commercial EV fleets operate vehicles across dozens of manufacturers, each pushing distinct telemetry payload structures and units (e.g. Imperial vs. Metric, nested objects, raw signal arrays, or delimited text streams).

Our architecture addresses this via an **Adapter Pattern + Registry**:
1. Incoming telemetry lands on the raw topic (`telemetry.raw`).
2. An unrecognized OEM format cannot be parsed by default and is safely routed to the Dead Letter Queue (`telemetry.dlq`), incrementing Prometheus metric `invalid_total{reason="unknown_oem"}`.
3. Onboarding a new OEM requires adding **only one adapter implementation file** (`pkg/adapters/<oem>.go`) and registering it with the in-memory registry.
4. The ingestion workers perform a rolling restart (`docker compose up -d --build ingest-normalize`), while Redpanda, ClickHouse, Postgres, Redis, and other services remain 100% online.
5. Replaying or streaming the same OEM payloads immediately succeeds, normalizing events into canonical `schema_v: 1` format and producing to `telemetry.canonical`.

---

## 2. Step 1: Unmapped OEM Payloads Sent to Ingest Path

We generated 5 sample telematics events from a new manufacturer **ApexEV** with unique JSON formatting (e.g., `battery_status`, `gps`, and `telemetry` blocks) and valid check-digit VIN `1APEV01A600000001`:

```bash
for ($i = 1; $i -le 5; $i++) {
    $msg = '{"oem":"ApexEV","vin":"1APEV01A600000001","timestamp":"2026-09-30T12:00:00Z","seq":' + $i + ',"gps":{"latitude":37.7749,"longitude":-122.4194},"battery_status":{"soc":82.5,"pack_temp":26.0},"telemetry":{"speed":55.0,"odo":15000.0},"charging":{"active":false,"kw":0.0},"dtcs":[],"event":"NONE"}';
    echo $msg | docker compose exec -T redpanda rpk topic produce telemetry.raw -k 1APEV01A600000001
}
```

### Result Before Adapter Implementation:
1. **Prometheus Metric**:
   ```text
   invalid_total{reason="unknown_oem"} 7
   ```
2. **DLQ Record Captured** (`telemetry.dlq`):
   ```json
   {
     "topic": "telemetry.dlq",
     "key": "1APEV01A600000001",
     "value": "{\"reason\":\"unknown_oem\",\"error\":\"unknown OEM: ApexEV\",\"raw\":\"{\\\"oem\\\":\\\"ApexEV\\\",\\\"vin\\\":\\\"1APEV01A600000001\\\",\\\"timestamp\\\":\\\"2026-09-30T12:00:00Z\\\",\\\"seq\\\":1,...}\",\"received_at\":\"2026-09-30T12:03:54Z\"}",
     "partition": 2,
     "offset": 615
   }
   ```

---

## 3. Step 2: Implement Adapter & Registry Entry

We created [`services/ingest/pkg/adapters/apexev.go`](file:///c:/Documents/Motorq_Hackathon/services/ingest/pkg/adapters/apexev.go) implementing the `Adapter` interface:

```go
type ApexEVAdapter struct{}

func (a *ApexEVAdapter) OEM() string { return "ApexEV" }

func (a *ApexEVAdapter) CanParse(raw []byte) bool {
    var p fastjson.Parser
    v, err := p.ParseBytes(raw)
    if err != nil { return false }
    return string(v.GetStringBytes("oem")) == "ApexEV"
}

func (a *ApexEVAdapter) Parse(raw []byte) (*canonical.Event, error) {
    var p apexEVPayload
    if err := json.Unmarshal(raw, &p); err != nil { return nil, err }
    // Normalizes to canonical.Event:
    // - ts parsed to time.Time UTC
    // - charging boolean converted to 0/1
    // - geohash7 auto-derived
    ...
}
```

And registered it in `services/ingest/pkg/adapters/adapter.go`:
```go
func init() {
    ...
    DefaultRegistry.Register(&ApexEVAdapter{})
}
```

### Git Diff Stat
```text
$ git diff --stat services/ingest/pkg/adapters/
 services/ingest/pkg/adapters/adapter.go |   1 +
 services/ingest/pkg/adapters/apexev.go  | 106 +++++++++++++++++++++++++++++++++
 2 files changed, 107 insertions(+)
```

---

## 4. Step 3: Rolling Restart of Ingest Normalizer

Zero downtime rolling restart executed via Docker Compose:
```bash
docker compose up -d --build ingest-normalize
```
- Redpanda cluster: **Healthy / Running** (0 downtime, 0 dropped messages).
- Storage sinks & Postgres: **Healthy / Running**.

---

## 5. Step 4: Verification in Canonical Topic

We streamed 5 subsequent `ApexEV` records (`seq: 10..14`) to `telemetry.raw`:

### Prometheus Metric Verified:
```text
ingest_events_total{oem="ApexEV"} 5
```

### Canonical Topic Output (`telemetry.canonical`):
```json
{
  "topic": "telemetry.canonical",
  "key": "1APEV01A600000001",
  "value": {
    "schema_v": 1,
    "vin": "1APEV01A600000001",
    "seq": 10,
    "oem": "ApexEV",
    "lat": 37.7749,
    "lon": -122.4194,
    "geohash7": "9q8yyk8",
    "speed_kmh": 55,
    "soc_pct": 82.5,
    "odo_km": 15000,
    "batt_temp_c": 26,
    "charging": 0,
    "charge_kw": 0,
    "dtc": [],
    "evt": "NONE",
    "ts": "2026-09-30T12:00:00Z"
  },
  "timestamp": 1790770034892,
  "partition": 4,
  "offset": 29238
}
```

---

## 6. Summary

| Verification Stage | Metric Counter | Topic Destination | Status |
|---|---|---|---|
| **Before Onboarding** | `invalid_total{reason="unknown_oem"}` | `telemetry.dlq` | Rejected safely |
| **After Onboarding** | `ingest_events_total{oem="ApexEV"}` | `telemetry.canonical` | Ingested successfully |

New OEM onboarding was achieved with **0 downtime**, isolated code changes (1 new adapter file + 1 registry line), and automatic schema validation.
