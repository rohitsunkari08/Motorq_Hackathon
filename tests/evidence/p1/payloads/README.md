# OEM Ingestion & Normalization Payloads

This directory contains raw payload samples from the 5 simulated OEM formats alongside their normalized output in the standardized canonical schema (`schema_v: 1`), per **NOTE.md §5.2 & §6.4**.

---

## 1. VoltX (JSON snake_case)
- **Raw Format**: Flat JSON, snake_case keys, ISO 8601 UTC timestamp, metric units (`km/h`, `%`, `km`, `°C`).
- **Files**:
  - Raw: [`VoltX_raw.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/VoltX_raw.json)
  - Canonical: [`VoltX_canonical.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/VoltX_canonical.json)

---

## 2. NordMotors (Nested JSON camelCase & Imperial Units)
- **Raw Format**: Deeply nested structure (`vehicle.id`, `position.{latitude, longitude}`, `battery.{level, tempF}`). Uses imperial units: `speedMph` (miles per hour), `odoMiles`, Fahrenheit temperature (`tempF`), and fractional SoC (0.0 to 1.0).
- **Conversions Applied**:
  - $\text{Speed}_{\text{km/h}} = \text{speedMph} \times 1.609344$
  - $\text{Odo}_{\text{km}} = \text{odoMiles} \times 1.609344$
  - $\text{SoC}_{\%} = \text{battery.level} \times 100.0$
  - $\text{Temp}_{^{\circ}\text{C}} = (\text{battery.tempF} - 32.0) \times \frac{5}{9}$
- **Files**:
  - Raw: [`NordMotors_raw.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/NordMotors_raw.json)
  - Canonical: [`NordMotors_canonical.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/NordMotors_canonical.json)

---

## 3. AsiaDrive (Pipe-Delimited String)
- **Raw Format**: Compact pipe-delimited telematics stream: `VIN|epoch_ms|lat|lon|kmh|soc|odo|tempC|chg_kw|DTCs;seq;evt`.
- **Conversions Applied**:
  - Timestamp parsed from millisecond epoch to RFC 3339 UTC.
  - Semicolon-delimited trailer parsed for diagnostic trouble codes, sequence number, and event classification.
- **Files**:
  - Raw: [`AsiaDrive_raw.txt`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/AsiaDrive_raw.txt)
  - Canonical: [`AsiaDrive_canonical.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/AsiaDrive_canonical.json)

---

## 4. EuroEV (Signal Array with Units)
- **Raw Format**: Flexible signal dictionary structure (`signals:[{name, value, unit}]`) with unix epoch seconds. Tolerates missing signals and dynamic ordering.
- **Conversions Applied**:
  - Array signal lookup and unit normalization.
  - Timestamp converted from seconds epoch to UTC ISO string.
- **Files**:
  - Raw: [`EuroEV_raw.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/EuroEV_raw.json)
  - Canonical: [`EuroEV_canonical.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/EuroEV_canonical.json)

---

## 5. ZephyrEV (Compact Short Keys & Permille SoC)
- **Raw Format**: Compact JSON with abbreviated keys (`v`, `t`, `sq`, `pos.{lat,lon}`, `spd`, `soc_pm`, `odo`, `tmp`, `chg`, `pwr`, `dtc`, `evt`). SoC expressed in permille (0–1000 $\permil$).
- **Conversions Applied**:
  - $\text{SoC}_{\%} = \frac{\text{soc\_pm}}{10.0}$
  - Millisecond epoch `t` to UTC ISO 8601.
- **Files**:
  - Raw: [`ZephyrEV_raw.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/ZephyrEV_raw.json)
  - Canonical: [`ZephyrEV_canonical.json`](file:///c:/Documents/Motorq_Hackathon/tests/evidence/p1/payloads/ZephyrEV_canonical.json)
