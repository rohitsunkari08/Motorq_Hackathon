"""ClickHouse Telemetry Repository
Performs analytical queries over high-scale telemetry and rollups.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from services.api.app.infra.clickhouse import clickhouse_client


class TelemetryRepo:
    async def get_vehicle_telemetry(
        self,
        vin: str,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch historical canonical telemetry records for a vehicle."""
        limit = min(max(1, limit), 500)
        clauses = ["vin = %(vin)s"]
        params = {"vin": vin, "limit": limit}

        if from_ts:
            clauses.append("ts >= %(from_ts)s")
            params["from_ts"] = from_ts
        if to_ts:
            clauses.append("ts <= %(to_ts)s")
            params["to_ts"] = to_ts

        where_sql = " AND ".join(clauses)
        query = f"""
            SELECT 
                ts,
                seq,
                geohash7,
                lat,
                lon,
                speed_kmh,
                soc_pct,
                odo_km,
                batt_temp_c,
                charging,
                charge_kw,
                dtc,
                evt
            FROM evc.telemetry
            WHERE {where_sql}
            ORDER BY ts DESC
            LIMIT %(limit)s;
        """

        result = await clickhouse_client.query(query, parameters=params)
        points = []
        for row in result.result_rows:
            points.append({
                "ts": row[0],
                "seq": int(row[1]),
                "geohash7": str(row[2]),
                "lat": float(row[3]) if row[3] is not None else None,
                "lon": float(row[4]) if row[4] is not None else None,
                "speed_kmh": float(row[5]),
                "soc_pct": float(row[6]),
                "odo_km": float(row[7]),
                "batt_temp_c": float(row[8]),
                "charging": int(row[9]),
                "charge_kw": float(row[10]),
                "dtc": list(row[11]) if row[11] is not None else [],
                "evt": str(row[12]),
            })
        return points

    async def get_fleet_kpis_from_daily(self, fleet_id: int) -> Dict[str, Any]:
        """Aggregate KPIs from ClickHouse vehicle_daily."""
        query = """
            SELECT 
                uniq(vin) AS active_vehicles,
                sum(kwh_used) AS total_kwh,
                count() AS total_days
            FROM evc.vehicle_daily
            WHERE day >= today() - 30;
        """
        try:
            res = await clickhouse_client.query(query)
            if res.result_rows and len(res.result_rows) > 0:
                row = res.result_rows[0]
                return {
                    "active_vehicles": int(row[0]),
                    "total_kwh": float(row[1] or 0.0),
                }
        except Exception:
            pass
        return {"active_vehicles": 0, "total_kwh": 0.0}


telemetry_repo = TelemetryRepo()
