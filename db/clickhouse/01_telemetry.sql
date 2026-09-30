CREATE DATABASE IF NOT EXISTS evc;

-- Hot store: canonical telemetry. Partition by day, order by (vin, ts) -> per-vehicle range scans + partition pruning.
-- Column TTL on lat/lon: precise location kept 30 days, geohash7 kept indefinitely per §5.4 (1)
CREATE TABLE IF NOT EXISTS evc.telemetry (
  vin FixedString(17),
  ts DateTime64(3,'UTC'),
  seq UInt64,
  oem LowCardinality(String),
  geohash7 String,
  lat Float32 TTL toDateTime(ts) + INTERVAL 30 DAY,
  lon Float32 TTL toDateTime(ts) + INTERVAL 30 DAY,
  speed_kmh Float32,
  soc_pct Float32,
  odo_km Float64,
  batt_temp_c Float32,
  charging UInt8,
  charge_kw Float32,
  dtc Array(LowCardinality(String)),
  evt LowCardinality(String)
) ENGINE = ReplacingMergeTree
PARTITION BY toYYYYMMDD(ts)
ORDER BY (vin, ts, seq)
TTL toDateTime(ts) + INTERVAL 365 DAY DELETE
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS evc.telemetry_1m (
  vin FixedString(17),
  minute DateTime('UTC'),
  soc_min AggregateFunction(min, Float32),
  soc_avg AggregateFunction(avg, Float32),
  kwh_proxy AggregateFunction(sum, Float32),
  n AggregateFunction(count)
) ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMMDD(minute)
ORDER BY (vin, minute);

CREATE MATERIALIZED VIEW IF NOT EXISTS evc.telemetry_1m_mv TO evc.telemetry_1m AS
SELECT
  vin,
  toStartOfMinute(ts) AS minute,
  minState(soc_pct) AS soc_min,
  avgState(soc_pct) AS soc_avg,
  sumState(toFloat32(charge_kw / 3600)) AS kwh_proxy,
  countState() AS n
FROM evc.telemetry
GROUP BY vin, minute;

-- §5.4 (2) Daily summary rollup table: partitioned by month, order by (vin, day)
CREATE TABLE IF NOT EXISTS evc.vehicle_daily (
  vin FixedString(17),
  day Date,
  distance_km Float32,
  kwh_used Float32,
  dc_fast_kwh Float32,
  ac_kwh Float32,
  avg_temp_c Float32,
  sessions UInt16,
  est_capacity_kwh Float32
) ENGINE = MergeTree
PARTITION BY toYYYYMM(day)
ORDER BY (vin, day)
SETTINGS index_granularity = 8192;

-- §5.4 (2) Charging session table: partitioned by month, order by (vin, start_ts)
CREATE TABLE IF NOT EXISTS evc.charge_session (
  vin FixedString(17),
  start_ts DateTime64(3, 'UTC'),
  end_ts DateTime64(3, 'UTC'),
  soc_start Float32,
  soc_end Float32,
  kwh_added Float32,
  max_kw Float32,
  charger_type LowCardinality(String)
) ENGINE = MergeTree
PARTITION BY toYYYYMM(start_ts)
ORDER BY (vin, start_ts)
SETTINGS index_granularity = 8192;
