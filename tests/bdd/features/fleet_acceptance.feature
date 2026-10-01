Feature: EV Fleet Charging & Battery-Health Copilot Acceptance

  As a Fleet Operations Manager and Platform Engineer
  I want guaranteed real-time safety alerts, privacy protection, data deduplication, and AI governance
  So that fleet uptime is maximized, regulations are met, and system reliability is provable.

  @alert
  Scenario: Range-risk alert detection within latency budget
    Given a monitored vehicle "1VXEV01A100000001" with battery capacity 75.0 kWh and SoH 95.0%
    When the vehicle telematics reports SoC dropping to 7.0% while distance to nearest charger is 24.0 km
    Then a "RANGE_RISK" alert is evaluated within 5.0 seconds
    And the alert severity is 1 with an immediate detour recommendation

  @dedupe
  Scenario: Duplicate telemetry payloads are deduplicated without double-counting
    Given a canonical telemetry event with VIN "1VXEV01A100000001" and sequence number 42001
    When the same event is received a second time within 5 seconds
    Then the deduplication engine identifies the duplicate sequence
    And the duplicate payload is discarded without corrupting fleet metrics

  @dlq
  Scenario: Unknown OEM format or malformed payload is routed to Dead Letter Queue
    Given a raw telemetry payload from an unmapped OEM "AlienMotors"
    When the normalization engine processes the unrecognized payload
    Then the event is rejected from the canonical stream
    And the payload is forwarded to the telemetry.dlq topic with reason "UNKNOWN_OEM"

  @privacy
  Scenario: Viewer role sees masked coarse location while Fleet Manager sees precise coordinates
    Given a vehicle located at precise latitude 37.774929 and longitude -122.419416
    When a user with role "viewer" requests the vehicle telematics status
    Then the coordinates are masked to geohash5 precision "9q8yy"
    When a user with role "fleet_manager" requests the vehicle telematics status
    Then the precise coordinates 37.774929 and -122.419416 are visible

  @erasure
  Scenario: Right-to-erasure scrubs vehicle and driver data across all polyglot stores
    Given a vehicle "1VXEV01A100000099" registered in Postgres, ClickHouse, and Redis
    When an authorized admin submits an erasure request for "1VXEV01A100000099"
    Then the vehicle status is marked erased in Postgres
    And the Redis latest-state key is deleted
    And the ClickHouse delete mutation is dispatched
    And an immutable audit entry is recorded with actor_type "user"

  @governance
  Scenario: Agent Copilot is strictly prohibited from approving charge plans
    Given a charge plan 101 with status "proposed"
    When an AI agent or user attempts to call "approve_charge_plan" through the copilot interface
    Then the guardrail blocks the request
    And the agent responds that charge plan approval requires explicit human UI authorization
    And the plan status remains "proposed"
