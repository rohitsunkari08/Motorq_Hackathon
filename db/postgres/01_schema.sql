-- Relational core, 3NF. Strong consistency (CP): ownership, plans, billing, audit.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE tenant (tenant_id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE subscription (sub_id SERIAL PRIMARY KEY, tenant_id INT NOT NULL REFERENCES tenant, plan TEXT NOT NULL, status TEXT NOT NULL, valid_to DATE NOT NULL);
CREATE TABLE fleet (fleet_id SERIAL PRIMARY KEY, tenant_id INT NOT NULL REFERENCES tenant, name TEXT NOT NULL, UNIQUE(tenant_id,name));
CREATE TABLE oem (oem_id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE, payload_format TEXT NOT NULL);
CREATE TABLE vehicle_model (model_id SERIAL PRIMARY KEY, oem_id INT NOT NULL REFERENCES oem, name TEXT NOT NULL, battery_kwh REAL NOT NULL, rated_range_km REAL NOT NULL, max_dc_kw REAL NOT NULL, UNIQUE(oem_id,name));
CREATE TABLE vehicle (vin CHAR(17) PRIMARY KEY CHECK (vin ~ '^[A-HJ-NPR-Z0-9]{17}$'), fleet_id INT NOT NULL REFERENCES fleet, model_id INT NOT NULL REFERENCES vehicle_model, model_year SMALLINT NOT NULL, erased_at TIMESTAMPTZ);
CREATE TABLE driver (driver_id SERIAL PRIMARY KEY, fleet_id INT NOT NULL REFERENCES fleet, pseudonym TEXT NOT NULL, erased_at TIMESTAMPTZ);
CREATE TABLE trip (trip_id BIGSERIAL PRIMARY KEY, vin CHAR(17) NOT NULL REFERENCES vehicle, driver_id INT REFERENCES driver, start_ts TIMESTAMPTZ NOT NULL, end_ts TIMESTAMPTZ, start_soc REAL, end_soc REAL, distance_km REAL);
CREATE TABLE charger (charger_id SERIAL PRIMARY KEY, network TEXT NOT NULL, geohash7 CHAR(7) NOT NULL, lat DOUBLE PRECISION NOT NULL, lon DOUBLE PRECISION NOT NULL, power_kw REAL NOT NULL);
CREATE TABLE tariff (tariff_id SERIAL PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE tariff_slot (tariff_id INT NOT NULL REFERENCES tariff, hour_start SMALLINT NOT NULL, hour_end SMALLINT NOT NULL, price_per_kwh NUMERIC(6,3) NOT NULL, PRIMARY KEY(tariff_id,hour_start));
CREATE TABLE app_user (user_id SERIAL PRIMARY KEY, tenant_id INT NOT NULL REFERENCES tenant, email TEXT NOT NULL UNIQUE, role TEXT NOT NULL CHECK (role IN ('admin','fleet_manager','viewer')), pw_hash TEXT NOT NULL);
CREATE TABLE alert (alert_id BIGSERIAL PRIMARY KEY, vin CHAR(17) NOT NULL REFERENCES vehicle, type TEXT NOT NULL, severity SMALLINT NOT NULL, raised_at TIMESTAMPTZ NOT NULL, resolved_at TIMESTAMPTZ, detail JSONB);
CREATE TABLE charge_plan (plan_id BIGSERIAL PRIMARY KEY, vin CHAR(17) NOT NULL REFERENCES vehicle, charger_id INT NOT NULL REFERENCES charger, start_ts TIMESTAMPTZ NOT NULL, end_ts TIMESTAMPTZ NOT NULL, target_soc REAL NOT NULL, est_cost NUMERIC(8,2) NOT NULL, baseline_cost NUMERIC(8,2) NOT NULL, status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','approved','rejected')), proposed_by TEXT NOT NULL, approved_by INT REFERENCES app_user);
CREATE TABLE soh_estimate (vin CHAR(17) NOT NULL REFERENCES vehicle, est_at DATE NOT NULL, soh_pct REAL NOT NULL, model_version TEXT NOT NULL, PRIMARY KEY(vin,est_at));
CREATE TABLE audit_log (audit_id BIGSERIAL PRIMARY KEY, ts TIMESTAMPTZ NOT NULL DEFAULT now(), actor TEXT NOT NULL, actor_type TEXT NOT NULL CHECK (actor_type IN ('user','agent','system')), action TEXT NOT NULL, resource TEXT NOT NULL, detail JSONB);
CREATE TABLE erasure_request (req_id SERIAL PRIMARY KEY, vin CHAR(17), driver_id INT, requested_at TIMESTAMPTZ NOT NULL DEFAULT now(), completed_at TIMESTAMPTZ);
CREATE TABLE doc_chunk (chunk_id SERIAL PRIMARY KEY, source TEXT NOT NULL, content TEXT NOT NULL, embedding vector(384));
CREATE INDEX ix_vehicle_fleet ON vehicle(fleet_id);
CREATE INDEX ix_alert_open ON alert(vin, raised_at DESC) WHERE resolved_at IS NULL;
CREATE INDEX ix_trip_vin_start ON trip(vin, start_ts DESC);
CREATE INDEX ix_charger_geo ON charger(geohash7);
CREATE INDEX ix_doc_embed ON doc_chunk USING hnsw (embedding vector_cosine_ops);

-- §5.4 (3) Postgres RLS policies on vehicle/alert/charge_plan/trip using current_setting('app.tenant_id')
ALTER TABLE vehicle ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert ENABLE ROW LEVEL SECURITY;
ALTER TABLE charge_plan ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip ENABLE ROW LEVEL SECURITY;

ALTER TABLE vehicle FORCE ROW LEVEL SECURITY;
ALTER TABLE alert FORCE ROW LEVEL SECURITY;
ALTER TABLE charge_plan FORCE ROW LEVEL SECURITY;
ALTER TABLE trip FORCE ROW LEVEL SECURITY;

CREATE POLICY vehicle_tenant_isolation ON vehicle
  FOR ALL
  USING (
    current_setting('app.bypass_rls', true) = 'on'
    OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
    OR fleet_id IN (
      SELECT f.fleet_id FROM fleet f
      WHERE f.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::int
    )
  )
  WITH CHECK (
    current_setting('app.bypass_rls', true) = 'on'
    OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
    OR fleet_id IN (
      SELECT f.fleet_id FROM fleet f
      WHERE f.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::int
    )
  );

CREATE POLICY alert_tenant_isolation ON alert
  FOR ALL
  USING (
    current_setting('app.bypass_rls', true) = 'on'
    OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
    OR vin IN (
      SELECT v.vin FROM vehicle v
      JOIN fleet f ON v.fleet_id = f.fleet_id
      WHERE f.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::int
    )
  )
  WITH CHECK (
    current_setting('app.bypass_rls', true) = 'on'
    OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
    OR vin IN (
      SELECT v.vin FROM vehicle v
      JOIN fleet f ON v.fleet_id = f.fleet_id
      WHERE f.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::int
    )
  );

CREATE POLICY charge_plan_tenant_isolation ON charge_plan
  FOR ALL
  USING (
    current_setting('app.bypass_rls', true) = 'on'
    OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
    OR vin IN (
      SELECT v.vin FROM vehicle v
      JOIN fleet f ON v.fleet_id = f.fleet_id
      WHERE f.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::int
    )
  )
  WITH CHECK (
    current_setting('app.bypass_rls', true) = 'on'
    OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
    OR vin IN (
      SELECT v.vin FROM vehicle v
      JOIN fleet f ON v.fleet_id = f.fleet_id
      WHERE f.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::int
    )
  );

CREATE POLICY trip_tenant_isolation ON trip
  FOR ALL
  USING (
    current_setting('app.bypass_rls', true) = 'on'
    OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
    OR vin IN (
      SELECT v.vin FROM vehicle v
      JOIN fleet f ON v.fleet_id = f.fleet_id
      WHERE f.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::int
    )
  )
  WITH CHECK (
    current_setting('app.bypass_rls', true) = 'on'
    OR NULLIF(current_setting('app.tenant_id', true), '') IS NULL
    OR vin IN (
      SELECT v.vin FROM vehicle v
      JOIN fleet f ON v.fleet_id = f.fleet_id
      WHERE f.tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::int
    )
  );
