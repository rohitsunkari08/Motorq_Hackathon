package alerts

import (
	"context"
	"testing"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
)

func TestChargerIndexNearest(t *testing.T) {
	ci := NewChargerIndex()

	// Add test chargers
	ci.AddCharger(Charger{ID: 1, Network: "NetA", Lat: 40.7128, Lon: -74.0060, PowerKW: 150})
	ci.AddCharger(Charger{ID: 2, Network: "NetB", Lat: 34.0522, Lon: -118.2437, PowerKW: 100})

	// Query close to NYC charger
	chg, dist, ok := ci.NearestCharger(40.7130, -74.0055)
	if !ok {
		t.Fatal("expected charger to be found")
	}
	if chg.ID != 1 {
		t.Errorf("expected charger ID 1, got %d", chg.ID)
	}
	if dist > 1.0 { // should be less than 1 km
		t.Errorf("expected distance < 1 km, got %f", dist)
	}
}

func TestDebouncer(t *testing.T) {
	d := NewDebouncer(10 * time.Minute)
	now := time.Now()

	vin := "1EEEV01A600000001"
	alertType := "LOW_SOC"

	// First attempt should emit
	if !d.ShouldEmit(vin, alertType, now) {
		t.Fatal("first alert should be emitted")
	}

	// Immediate second attempt should be suppressed
	if d.ShouldEmit(vin, alertType, now.Add(1*time.Minute)) {
		t.Fatal("second alert within 10 min should be suppressed")
	}

	// Different alert type should emit
	if !d.ShouldEmit(vin, "HARSH_BRAKE", now.Add(1*time.Minute)) {
		t.Fatal("different alert type should be emitted")
	}

	// After 10 minutes should emit
	if !d.ShouldEmit(vin, alertType, now.Add(11*time.Minute)) {
		t.Fatal("alert after 11 min should be emitted")
	}
}

func TestRuleEngineRangeRiskAndLowSOC(t *testing.T) {
	ci := NewChargerIndex()
	// Charger located at ~20 km away
	ci.AddCharger(Charger{ID: 1, Network: "TestNet", Lat: 40.7128, Lon: -74.0060, PowerKW: 150})

	params := NewVehicleParamsStore(nil)
	windows := NewWindowManager()
	engine := NewRuleEngine(ci, params, windows)

	ctx := context.Background()

	// Vehicle at 40.7128, -73.7660 (approx 20 km away)
	// SOC = 2.0% -> predicted range with 75 kWh, 0.98 SoH, 0.18 kWh/km = (0.02 * 75 * 0.98) / 0.18 = 8.16 km
	// Charger distance = ~20 km. 8.16 km < 1.2 * 20 km (24 km) -> RANGE_RISK!
	// Also SOC 2.0% < 15.0% -> LOW_SOC!
	ev := &canonical.Event{
		SchemaV:   1,
		VIN:       "1EEEV01A600000001",
		TS:        time.Now().UTC(),
		Lat:       40.7128,
		Lon:       -73.7660,
		SOCPct:    2.0,
		SpeedKMH:  45.0,
		BattTempC: 30.0,
		Charging:  0,
		Evt:       "NONE",
	}

	alerts := engine.EvaluateRules(ctx, ev)
	if len(alerts) != 2 {
		t.Fatalf("expected 2 alerts (RANGE_RISK and LOW_SOC), got %d", len(alerts))
	}

	types := map[string]bool{}
	for _, a := range alerts {
		types[a.Type] = true
	}

	if !types[TypeRangeRisk] {
		t.Error("expected RANGE_RISK alert")
	}
	if !types[TypeLowSOC] {
		t.Error("expected LOW_SOC alert")
	}
}

func TestRuleEngineThermal(t *testing.T) {
	ci := NewChargerIndex()
	params := NewVehicleParamsStore(nil)
	windows := NewWindowManager()
	engine := NewRuleEngine(ci, params, windows)

	ctx := context.Background()
	now := time.Now().UTC()
	vin := "1EEEV01A600000002"

	// Event 1: temp > 50C at T-65s
	ev1 := &canonical.Event{
		SchemaV:   1,
		VIN:       vin,
		TS:        now.Add(-65 * time.Second),
		SOCPct:    80.0,
		BattTempC: 52.0,
		Charging:  0,
		Evt:       "NONE",
	}
	engine.EvaluateRules(ctx, ev1)

	// Event 2: temp > 50C at T-0s (sustained > 60s)
	ev2 := &canonical.Event{
		SchemaV:   1,
		VIN:       vin,
		TS:        now,
		SOCPct:    79.5,
		BattTempC: 53.5,
		Charging:  0,
		Evt:       "NONE",
	}
	alerts := engine.EvaluateRules(ctx, ev2)

	foundThermal := false
	for _, a := range alerts {
		if a.Type == TypeThermal {
			foundThermal = true
			if a.Severity != SeverityHigh {
				t.Errorf("expected HIGH severity for thermal, got %s", a.Severity)
			}
		}
	}

	if !foundThermal {
		t.Error("expected THERMAL alert for sustained high temperature")
	}
}

func TestRuleEngineRapidDropAndHarshBrake(t *testing.T) {
	ci := NewChargerIndex()
	params := NewVehicleParamsStore(nil)
	windows := NewWindowManager()
	engine := NewRuleEngine(ci, params, windows)

	ctx := context.Background()
	now := time.Now().UTC()
	vin := "1EEEV01A600000003"

	// Initial event: SOC = 60%, 2 minutes ago
	ev1 := &canonical.Event{
		SchemaV:   1,
		VIN:       vin,
		TS:        now.Add(-2 * time.Minute),
		SOCPct:    60.0,
		SpeedKMH:  25.0,
		BattTempC: 28.0,
		Charging:  0,
		Evt:       "NONE",
	}
	engine.EvaluateRules(ctx, ev1)

	// Current event: SOC = 50% (drop of 10% > 8%), Speed = 20 km/h (< 30), Evt = HARSH_BRAKE
	ev2 := &canonical.Event{
		SchemaV:   1,
		VIN:       vin,
		TS:        now,
		SOCPct:    50.0,
		SpeedKMH:  20.0,
		BattTempC: 29.0,
		Charging:  0,
		Evt:       "HARSH_BRAKE",
	}
	alerts := engine.EvaluateRules(ctx, ev2)

	types := map[string]bool{}
	for _, a := range alerts {
		types[a.Type] = true
	}

	if !types[TypeRapidDrop] {
		t.Error("expected RAPID_DROP alert")
	}
	if !types[TypeHarshBrake] {
		t.Error("expected HARSH_BRAKE alert")
	}
}
