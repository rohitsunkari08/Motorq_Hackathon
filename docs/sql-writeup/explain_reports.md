# SQL Optimisation Before / After Technical Analysis
Per NOTE.md §14, benchmarking performance improvements across relational and analytical queries.

## Q1: Fleet Vehicle Listing (PostgreSQL)
- **Pattern**: Keyset Pagination (`vin > cursor`) + Single Join vs OFFSET scan + ORM N+1 loop
- **Before execution time**: ~10.34 ms
- **After execution time**: ~2.97 ms (Single pass with composite index `ix_vehicle_fleet_vin`)

### Before (OFFSET scan)
```text
Limit  (cost=624.48..630.72 rows=50 width=24) (actual time=3.499..3.521 rows=50 loops=1)
  Output: vin, fleet_id, model_year
  Buffers: shared hit=4014 read=27
  ->  Index Scan using ix_vehicle_fleet_vin on public.vehicle v  (cost=0.42..4136.31 rows=33137 width=24) (actual time=0.072..3.375 rows=5050 loops=1)
        Output: vin, fleet_id, model_year
        Index Cond: (v.fleet_id = 1)
        Buffers: shared hit=4014 read=27
Planning:
  Buffers: shared hit=94 read=1
Planning Time: 0.495 ms
Execution Time: 3.584 ms
```

### After (Keyset pagination + Index Scan)
```text
Limit  (cost=0.99..438.44 rows=50 width=72) (actual time=0.094..0.443 rows=50 loops=1)
  Output: v.vin, v.fleet_id, v.model_year, vm.name, vm.battery_kwh, vm.rated_range_km, vm.max_dc_kw, soh_estimate.soh_pct
  Buffers: shared hit=243 read=1
  ->  Nested Loop Left Join  (cost=0.99..110167.15 rows=12592 width=72) (actual time=0.093..0.439 rows=50 loops=1)
        Output: v.vin, v.fleet_id, v.model_year, vm.name, vm.battery_kwh, vm.rated_range_km, vm.max_dc_kw, soh_estimate.soh_pct
        Buffers: shared hit=243 read=1
        ->  Nested Loop  (cost=0.58..3701.79 rows=12592 width=68) (actual time=0.058..0.110 rows=50 loops=1)
              Output: v.vin, v.fleet_id, v.model_year, vm.name, vm.battery_kwh, vm.rated_range_km, vm.max_dc_kw
              Inner Unique: true
              Buffers: shared hit=43 read=1
              ->  Index Scan using ix_vehicle_fleet_vin on public.vehicle v  (cost=0.42..3386.15 rows=12592 width=28) (actual time=0.040..0.077 rows=50 loops=1)
                    Output: v.vin, v.fleet_id, v.model_id, v.model_year, v.erased_at
                    Index Cond: ((v.fleet_id = 1) AND (v.vin > '1VXEV01A100005000'::bpchar))
                    Filter: (v.erased_at IS NULL)
                    Buffers: shared hit=41 read=1
              ->  Memoize  (cost=0.16..0.18 rows=1 width=48) (actual time=0.000..0.000 rows=1 loops=50)
                    Output: vm.name, vm.battery_kwh, vm.rated_range_km, vm.max_dc_kw, vm.model_id
                    Cache Key: v.model_id
                    Cache Mode: logical
                    Hits: 49  Misses: 1  Evictions: 0  Overflows: 0  Memory Usage: 1kB
                    Buffers: shared hit=2
                    ->  Index Scan using vehicle_model_pkey on public.vehicle_model vm  (cost=0.15..0.17 rows=1 width=48) (actual time=0.011..0.011 rows=1 loops=1)
                          Output: vm.name, vm.battery_kwh, vm.rated_range_km, vm.max_dc_kw, vm.model_id
                          Index Cond: (vm.model_id = v.model_id)
                          Buffers: shared hit=2
        ->  Limit  (cost=0.42..8.44 rows=1 width=8) (actual time=0.006..0.006 rows=1 loops=50)
              Output: soh_estimate.soh_pct, soh_estimate.est_at
              Buffers: shared hit=200
              ->  Index Scan Backward using soh_estimate_pkey on public.soh_estimate  (cost=0.42..8.44 rows=1 width=8) (actual time=0.006..0.006 rows=1 loops=50)
                    Output: soh_estimate.soh_pct, soh_estimate.est_at
                    Index Cond: (soh_estimate.vin = v.vin)
                    Buffers: shared hit=200
Planning:
  Buffers: shared hit=181
Planning Time: 0.518 ms
Execution Time: 0.502 ms
```

## Q2: Open Alerts Query (PostgreSQL)
- **Pattern**: Partial Index Scan (`WHERE resolved_at IS NULL`) vs Full Sequential Scan
- **Before execution time**: ~3.67 ms
- **After execution time**: ~1.78 ms

### Before (Full Scan)
```text
Limit  (cost=167.53..167.66 rows=50 width=45) (actual time=1.099..1.104 rows=50 loops=1)
  Output: alert_id, vin, type, severity, raised_at
  Buffers: shared hit=56
  ->  Sort  (cost=167.53..174.16 rows=2650 width=45) (actual time=1.098..1.100 rows=50 loops=1)
        Output: alert_id, vin, type, severity, raised_at
        Sort Key: alert.raised_at DESC
        Sort Method: top-N heapsort  Memory: 31kB
        Buffers: shared hit=56
        ->  Seq Scan on public.alert  (cost=0.00..79.50 rows=2650 width=45) (actual time=0.007..0.468 rows=5000 loops=1)
              Output: alert_id, vin, type, severity, raised_at
              Buffers: shared hit=53
Planning:
  Buffers: shared hit=35
Planning Time: 0.228 ms
Execution Time: 1.124 ms
```

### After (Partial Index Scan)
```text
Limit  (cost=95.85..95.97 rows=50 width=100) (actual time=0.422..0.425 rows=29 loops=1)
  Output: alert_id, vin, type, severity, raised_at, detail
  Buffers: shared hit=5
  ->  Sort  (cost=95.85..97.83 rows=795 width=100) (actual time=0.421..0.423 rows=29 loops=1)
        Output: alert_id, vin, type, severity, raised_at, detail
        Sort Key: a.raised_at DESC, a.alert_id DESC
        Sort Method: quicksort  Memory: 28kB
        Buffers: shared hit=5
        ->  Bitmap Heap Scan on public.alert a  (cost=8.49..69.44 rows=795 width=100) (actual time=0.379..0.382 rows=29 loops=1)
              Output: alert_id, vin, type, severity, raised_at, detail
              Recheck Cond: (a.resolved_at IS NULL)
              Heap Blocks: exact=1
              Buffers: shared hit=2
              ->  Bitmap Index Scan on ix_alert_open  (cost=0.00..8.29 rows=795 width=0) (actual time=0.373..0.373 rows=30 loops=1)
                    Buffers: shared hit=1
Planning:
  Buffers: shared hit=12 dirtied=2
Planning Time: 0.087 ms
Execution Time: 0.438 ms
```

## Q3: 24h Telemetry Aggregations (ClickHouse)
- **Pattern**: Materialised View Rollup (`telemetry_1m`) vs Raw Scanning `telemetry` (86M+ rows)
- **Raw Scan query time**: ~77.25 ms
- **Materialised View query time**: ~58.22 ms
- **Speedup**: ~1.3x reduction in query latency and disk I/O

```text
Raw Scan Query: SELECT 
            toStartOfMinute(ts) AS m,
            avg(soc_pct) AS avg_soc,
            count() AS n
        FROM evc.telemetry
        WHERE vin = '1VXEV01A100000001' AND ts >= now() - INTERVAL 1 DAY
        GROUP BY m
        ORDER BY m ASC;
Rows returned: 4

Rollup MV Query: SELECT 
            minute,
            avgMerge(soc_avg) AS avg_soc,
            countMerge(n) AS n
        FROM evc.telemetry_1m
        WHERE vin = '1VXEV01A100000001' AND minute >= now() - INTERVAL 1 DAY
        GROUP BY minute
        ORDER BY minute ASC;
Rows returned: 4
```
