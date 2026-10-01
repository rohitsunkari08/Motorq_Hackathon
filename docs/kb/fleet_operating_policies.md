# Fleet Operating Policies and Governance

## Fleet Roles and Permissions (RBAC)

### 1. Fleet Administrator (`admin`)
- Full administrative access across all tenant fleet resources.
- Authorized to trigger compliance erasures (GDPR / DPDP Act right-to-erasure).
- Access to raw audit logs, system configurations, and cross-fleet differential privacy benchmarks.
- Can approve or reject charge plans and override dispatch parameters.

### 2. Fleet Manager (`fleet_manager`)
- Full operational control over vehicles, chargers, and drivers assigned to their specific tenant.
- Can view unmasked, real-time precise GPS locations and detailed telemetry.
- **Exclusive human authority to approve or reject proposed charge plans.**
- Reviews and acknowledges critical and high-severity fleet alerts.

### 3. Viewer (`viewer`)
- Read-only operational visibility over tenant fleet data.
- **Location Masking**: Precision coordinates (lat/lon) are masked to Geohash Level 5 (~4.9km bounding area) to protect driver privacy.
- Cannot approve charge plans or initiate configuration changes.

## Charge Plan Governance and AI Guardrails
- **Human-in-the-Loop Principle**: The Copilot AI agent operates strictly as an advisory system.
- The agent may inspect fleet status, query diagnostic codes, search the knowledge base, and calculate/propose optimal charge plans using Dynamic Programming.
- **The AI agent is structurally prohibited from approving, rejecting, executing, or modifying charge plans, or issuing erasure requests.**
- Only an authenticated human user holding `fleet_manager` or `admin` credentials can transition a plan from `proposed` to `approved` or `rejected`.

## Alert Classification and Escalation Matrix

### 1. `RANGE_RISK` (Severity 1 - CRITICAL)
- **Condition**: Predicted reachable range falls below 1.2x the distance to the nearest operational charger.
  `predicted_range = (soc / 100) * capacity_kwh * soh_pct / eff_kwh_per_km < 1.2 * min_charger_dist`
- **Action**: Immediate dispatch notification, reroute vehicle to nearest reachable charger, driver alert.

### 2. `THERMAL` (Severity 2 - HIGH)
- **Condition**: Traction battery pack temperature exceeds 50°C for longer than 60 continuous seconds.
- **Action**: Halt DC fast-charging or limit maximum charging rate to 10 kW until battery cools below 42°C.

### 3. `LOW_SOC` (Severity 2 - WARN)
- **Condition**: State of charge drops below 15% during operational shift.
- **Action**: Flag vehicle in fleet dashboard, recommend nearest depot or public charging facility.

### 4. `RAPID_DROP` (Severity 2 - WARN)
- **Condition**: SoC drops by greater than 8% within 5 minutes while vehicle speed is under 30 km/h (indicates parasitic drain or cell failure).
- **Action**: Flag for immediate workshop diagnostic scan.

### 5. `HARSH_BRAKE` (Severity 3 - INFO)
- **Condition**: Deceleration event exceeding 0.45g.
- **Action**: Logged for driver safety scoring and coaching.
