-- §5.4 (4) Seed tenants (3), users (admin/fleet_manager/viewer per tenant), fleets, tariffs, OEMs and models

-- 1. Tenants (3)
INSERT INTO tenant (tenant_id, name) VALUES
  (1, 'VoltFleet Logistics'),
  (2, 'MetroDelivery Corp'),
  (3, 'GreenHaul Transit')
ON CONFLICT (tenant_id) DO UPDATE SET name = EXCLUDED.name;

-- 2. Subscriptions
INSERT INTO subscription (sub_id, tenant_id, plan, status, valid_to) VALUES
  (1, 1, 'enterprise', 'active', '2028-12-31'),
  (2, 2, 'pro', 'active', '2028-12-31'),
  (3, 3, 'pro', 'active', '2028-12-31')
ON CONFLICT (sub_id) DO NOTHING;

-- 3. Fleets (at least one per tenant)
INSERT INTO fleet (fleet_id, tenant_id, name) VALUES
  (1, 1, 'VoltFleet Alpha'),
  (2, 2, 'MetroDelivery Metro'),
  (3, 3, 'GreenHaul Regional')
ON CONFLICT (fleet_id) DO NOTHING;

-- 4. Five OEMs per §5.2
INSERT INTO oem (oem_id, name, payload_format) VALUES
  (1, 'VoltX', 'json_flat'),
  (2, 'NordMotors', 'json_nested_camel'),
  (3, 'AsiaDrive', 'pipe_delimited'),
  (4, 'EuroEV', 'signals_array'),
  (5, 'ZephyrEV', 'short_keys_permille')
ON CONFLICT (oem_id) DO NOTHING;

-- 5. Vehicle Models (representative specs per OEM, 40-100 kWh battery)
INSERT INTO vehicle_model (model_id, oem_id, name, battery_kwh, rated_range_km, max_dc_kw) VALUES
  (1, 1, 'VoltX Hyper-e', 75.0, 420.0, 150.0),
  (2, 2, 'NordMotors Polar-4', 82.0, 450.0, 135.0),
  (3, 3, 'AsiaDrive Express-V', 60.0, 350.0, 100.0),
  (4, 4, 'EuroEV Continental', 90.0, 500.0, 175.0),
  (5, 5, 'ZephyrEV Aero-6', 50.0, 300.0, 80.0)
ON CONFLICT (model_id) DO NOTHING;

-- 6. Three Tariffs per §5.3
INSERT INTO tariff (tariff_id, name) VALUES
  (1, 'Commercial TOU Default'),
  (2, 'Ultra Off-Peak Fleet'),
  (3, 'Flat Commercial')
ON CONFLICT (tariff_id) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO tariff_slot (tariff_id, hour_start, hour_end, price_per_kwh) VALUES
  -- Tariff 1: TOU Default (Off-peak: 0-6, Normal: 6-14, Peak: 14-20, Normal: 20-24)
  (1, 0, 6, 0.080),
  (1, 6, 14, 0.150),
  (1, 14, 20, 0.280),
  (1, 20, 24, 0.140),
  -- Tariff 2: Ultra Off-Peak
  (2, 0, 7, 0.050),
  (2, 7, 16, 0.180),
  (2, 16, 21, 0.320),
  (2, 21, 24, 0.120),
  -- Tariff 3: Flat Commercial
  (3, 0, 24, 0.160)
ON CONFLICT (tariff_id, hour_start) DO NOTHING;

-- 7. App Users: admin, fleet_manager, viewer per tenant (Password: 'Password123!')
-- Hash: $argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA
INSERT INTO app_user (tenant_id, email, role, pw_hash) VALUES
  -- Tenant 1
  (1, 'admin@voltfleet.com', 'admin', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA'),
  (1, 'manager@voltfleet.com', 'fleet_manager', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA'),
  (1, 'viewer@voltfleet.com', 'viewer', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA'),
  -- Tenant 2
  (2, 'admin@metrohaul.com', 'admin', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA'),
  (2, 'manager@metrohaul.com', 'fleet_manager', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA'),
  (2, 'viewer@metrohaul.com', 'viewer', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA'),
  -- Tenant 3
  (3, 'admin@greenhaul.com', 'admin', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA'),
  (3, 'manager@greenhaul.com', 'fleet_manager', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA'),
  (3, 'viewer@greenhaul.com', 'viewer', '$argon2id$v=19$m=65536,t=3,p=4$bZcacvyaexAfisgXbO/tyg$AXNXXXWZyWucmQMqLAa2phb9uNv10aGlCTtuMSyqoJA')
ON CONFLICT (email) DO NOTHING;

-- Advance sequences
SELECT setval('tenant_tenant_id_seq', COALESCE((SELECT MAX(tenant_id) FROM tenant), 1));
SELECT setval('subscription_sub_id_seq', COALESCE((SELECT MAX(sub_id) FROM subscription), 1));
SELECT setval('fleet_fleet_id_seq', COALESCE((SELECT MAX(fleet_id) FROM fleet), 1));
SELECT setval('oem_oem_id_seq', COALESCE((SELECT MAX(oem_id) FROM oem), 1));
SELECT setval('vehicle_model_model_id_seq', COALESCE((SELECT MAX(model_id) FROM vehicle_model), 1));
SELECT setval('tariff_tariff_id_seq', COALESCE((SELECT MAX(tariff_id) FROM tariff), 1));
SELECT setval('app_user_user_id_seq', COALESCE((SELECT MAX(user_id) FROM app_user), 1));
