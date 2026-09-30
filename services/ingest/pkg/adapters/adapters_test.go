package adapters_test

import (
	"math"
	"testing"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/adapters"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/validation"
)

func makeTestVIN(base string) string {
	chk, _ := validation.ComputeVINCheckDigit(base)
	b := []byte(base)
	b[8] = chk
	return string(b)
}

func TestVoltXAdapter(t *testing.T) {
	vin := makeTestVIN("1VXEV0000AA000001")
	raw := []byte(`{
		"oem": "VoltX",
		"vin": "` + vin + `",
		"ts": "2026-09-30T10:00:00Z",
		"seq": 101,
		"lat": 37.7749,
		"lon": -122.4194,
		"speed_kmh": 65.5,
		"soc_pct": 78.4,
		"odo_km": 12500.5,
		"batt_temp_c": 26.5,
		"charging": 0,
		"charge_kw": 0.0,
		"dtc": ["P0A1F"],
		"evt": "NONE"
	}`)

	adapter := &adapters.VoltXAdapter{}
	if !adapter.CanParse(raw) {
		t.Fatal("VoltX CanParse failed")
	}

	event, err := adapter.Parse(raw)
	if err != nil {
		t.Fatalf("VoltX Parse failed: %v", err)
	}

	if event.OEM != "VoltX" || event.VIN != vin || event.Seq != 101 {
		t.Errorf("VoltX parsed event mismatch: %+v", event)
	}
	if event.Geohash7 == "" {
		t.Errorf("VoltX geohash7 not computed: %+v", event)
	}
	if err := event.Validate(); err != nil {
		t.Errorf("VoltX canonical event failed validation: %v", err)
	}
}

func TestNordMotorsAdapter(t *testing.T) {
	vin := makeTestVIN("1NMEV0000AA000002")
	raw := []byte(`{
		"oem": "NordMotors",
		"vehicle": {"id": "` + vin + `"},
		"time": "2026-09-30T10:00:00Z",
		"seq": 202,
		"position": {"latitude": 45.5017, "longitude": -73.5673},
		"speedMph": 50.0,
		"odoMiles": 10000.0,
		"battery": {"level": 0.55, "tempF": 77.0},
		"charging": true,
		"chargeKw": 50.0,
		"dtcs": ["P0123"],
		"event": "FAST_CHARGE"
	}`)

	adapter := &adapters.NordMotorsAdapter{}
	if !adapter.CanParse(raw) {
		t.Fatal("NordMotors CanParse failed")
	}

	event, err := adapter.Parse(raw)
	if err != nil {
		t.Fatalf("NordMotors Parse failed: %v", err)
	}

	if event.OEM != "NordMotors" || event.VIN != vin || event.Seq != 202 {
		t.Errorf("NordMotors event mismatch: %+v", event)
	}
	// Check conversions
	// 50 mph ~ 80.47 km/h
	if math.Abs(event.SpeedKMH-80.47) > 0.1 {
		t.Errorf("NordMotors speed conversion mismatch, got %f", event.SpeedKMH)
	}
	// 10000 miles ~ 16093.44 km
	if math.Abs(event.OdoKM-16093.44) > 0.1 {
		t.Errorf("NordMotors odo conversion mismatch, got %f", event.OdoKM)
	}
	// 0.55 level = 55.0%
	if math.Abs(event.SOCPct-55.0) > 0.01 {
		t.Errorf("NordMotors soc conversion mismatch, got %f", event.SOCPct)
	}
	// 77 F = 25.0 C
	if math.Abs(event.BattTempC-25.0) > 0.1 {
		t.Errorf("NordMotors temp conversion mismatch, got %f", event.BattTempC)
	}
	if event.Charging != 1 {
		t.Errorf("NordMotors charging boolean conversion mismatch, got %d", event.Charging)
	}
	if err := event.Validate(); err != nil {
		t.Errorf("NordMotors canonical event failed validation: %v", err)
	}
}

func TestAsiaDriveAdapter(t *testing.T) {
	vin := makeTestVIN("1ADEV0000AA000003")
	nowMs := time.Now().UTC().UnixMilli()
	// Format: VIN|epoch_ms|lat|lon|kmh|soc|odo|tempC|chg_kw|DTCs;seq;evt
	raw := []byte(vin + `|` + time.Now().Format("2006") + `|35.6762|139.6503|45.0|60.5|23000.0|27.5|0.0|;303;NONE`)
	// Let's use valid epoch_ms
	raw = []byte(vin + `|1727697600000|35.6762|139.6503|45.0|60.5|23000.0|27.5|0.0|P0A1F;303;NONE`)
	_ = nowMs

	adapter := &adapters.AsiaDriveAdapter{}
	if !adapter.CanParse(raw) {
		t.Fatal("AsiaDrive CanParse failed")
	}

	event, err := adapter.Parse(raw)
	if err != nil {
		t.Fatalf("AsiaDrive Parse failed: %v", err)
	}

	if event.OEM != "AsiaDrive" || event.VIN != vin || event.Seq != 303 {
		t.Errorf("AsiaDrive parsed event mismatch: %+v", event)
	}
	if len(event.DTC) != 1 || event.DTC[0] != "P0A1F" {
		t.Errorf("AsiaDrive DTC parse mismatch: %+v", event.DTC)
	}
	if err := event.Validate(); err != nil {
		t.Errorf("AsiaDrive canonical event failed validation: %v", err)
	}
}

func TestEuroEVAdapter(t *testing.T) {
	vin := makeTestVIN("1EEEV0000AA000004")
	raw := []byte(`{
		"oem": "EuroEV",
		"vin": "` + vin + `",
		"timestamp": 1727697600,
		"seq": 404,
		"signals": [
			{"name": "lat", "value": 48.8566, "unit": "deg"},
			{"name": "lon", "value": 2.3522, "unit": "deg"},
			{"name": "speed", "value": 55.0, "unit": "km/h"},
			{"name": "soc", "value": 72.0, "unit": "pct"},
			{"name": "odo", "value": 8500.0, "unit": "km"},
			{"name": "temp", "value": 22.0, "unit": "c"},
			{"name": "charging", "value": 0, "unit": ""},
			{"name": "charge_kw", "value": 0.0, "unit": "kw"},
			{"name": "dtc", "value": "P0100", "unit": ""},
			{"name": "evt", "value": "NONE", "unit": ""}
		]
	}`)

	adapter := &adapters.EuroEVAdapter{}
	if !adapter.CanParse(raw) {
		t.Fatal("EuroEV CanParse failed")
	}

	event, err := adapter.Parse(raw)
	if err != nil {
		t.Fatalf("EuroEV Parse failed: %v", err)
	}

	if event.OEM != "EuroEV" || event.VIN != vin || event.Seq != 404 {
		t.Errorf("EuroEV parsed event mismatch: %+v", event)
	}
	if event.SOCPct != 72.0 || event.SpeedKMH != 55.0 {
		t.Errorf("EuroEV signal values mismatch: %+v", event)
	}
	if err := event.Validate(); err != nil {
		t.Errorf("EuroEV canonical event failed validation: %v", err)
	}
}

func TestZephyrEVAdapter(t *testing.T) {
	vin := makeTestVIN("1ZZEV0000AA000005")
	raw := []byte(`{
		"oem": "ZephyrEV",
		"v": "` + vin + `",
		"t": 1727697600000,
		"sq": 505,
		"pos": {"lat": 51.5074, "lon": -0.1278},
		"spd": 48.0,
		"soc_pm": 845,
		"odo": 14200.0,
		"tmp": 24.5,
		"chg": 0,
		"pwr": 0.0,
		"dtc": ["P0300"],
		"evt": "NONE"
	}`)

	adapter := &adapters.ZephyrEVAdapter{}
	if !adapter.CanParse(raw) {
		t.Fatal("ZephyrEV CanParse failed")
	}

	event, err := adapter.Parse(raw)
	if err != nil {
		t.Fatalf("ZephyrEV Parse failed: %v", err)
	}

	if event.OEM != "ZephyrEV" || event.VIN != vin || event.Seq != 505 {
		t.Errorf("ZephyrEV parsed event mismatch: %+v", event)
	}
	// 845 permille = 84.5%
	if event.SOCPct != 84.5 {
		t.Errorf("ZephyrEV permille SoC mismatch, expected 84.5, got %f", event.SOCPct)
	}
	if err := event.Validate(); err != nil {
		t.Errorf("ZephyrEV canonical event failed validation: %v", err)
	}
}

func TestRegistryDetectAndParse(t *testing.T) {
	vin := makeTestVIN("1VXEV0000AA000006")
	voltxRaw := []byte(`{"oem": "VoltX", "vin": "` + vin + `", "ts": "2026-09-30T10:00:00Z", "seq": 1, "lat": 37.77, "lon": -122.41, "speed_kmh": 40.0, "soc_pct": 80.0, "odo_km": 100.0, "batt_temp_c": 25.0, "charging": 0, "charge_kw": 0.0, "dtc": [], "evt": "NONE"}`)

	// Detect by OEM in payload
	event, err := adapters.DefaultRegistry.DetectAndParse("", voltxRaw)
	if err != nil {
		t.Fatalf("registry detect failed: %v", err)
	}
	if event.OEM != "VoltX" {
		t.Errorf("expected VoltX OEM, got %s", event.OEM)
	}

	// Unknown OEM
	badOEMRaw := []byte(`{"oem": "FictionalAlienMotors", "vin": "` + vin + `"}`)
	_, err = adapters.DefaultRegistry.DetectAndParse("", badOEMRaw)
	if err == nil {
		t.Fatal("expected error on unknown OEM, got nil")
	}
}
