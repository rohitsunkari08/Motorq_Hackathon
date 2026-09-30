package normalizer_test

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/adapters"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/dedupe"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/validation"
)

func makeTestVIN(base string) string {
	chk, _ := validation.ComputeVINCheckDigit(base)
	b := []byte(base)
	b[8] = chk
	return string(b)
}

func TestNormalizerPipelineLogic(t *testing.T) {
	registry := adapters.DefaultRegistry
	deduper := dedupe.NewPartitionBloomDeduper(1000, 0.001)

	// 1. Valid VoltX event
	vin1 := makeTestVIN("1VXEV0000AA000001")
	voltxJSON := []byte(`{
		"oem": "VoltX",
		"vin": "` + vin1 + `",
		"ts": "` + time.Now().UTC().Format(time.RFC3339) + `",
		"seq": 1,
		"lat": 37.77,
		"lon": -122.41,
		"speed_kmh": 50.0,
		"soc_pct": 75.0,
		"odo_km": 1000.0,
		"batt_temp_c": 25.0,
		"charging": 0,
		"charge_kw": 0.0,
		"dtc": [],
		"evt": "NONE"
	}`)

	evt, err := registry.DetectAndParse("", voltxJSON)
	if err != nil {
		t.Fatalf("failed parsing VoltX: %v", err)
	}
	if err := evt.Validate(); err != nil {
		t.Fatalf("failed validating canonical event: %v", err)
	}
	if deduper.IsDuplicate(0, evt.VIN, evt.Seq) {
		t.Fatalf("should not be duplicate on first attempt")
	}

	// 2. Duplicate detection
	if !deduper.IsDuplicate(0, evt.VIN, evt.Seq) {
		t.Fatalf("should be detected as duplicate on second attempt")
	}

	// 3. Corrupted VIN -> DLQ trigger
	badVIN := []byte(vin1)
	if badVIN[8] == '0' {
		badVIN[8] = '1'
	} else {
		badVIN[8] = '0'
	}
	badVINEvent := *evt
	badVINEvent.VIN = string(badVIN)
	if err := badVINEvent.Validate(); err == nil {
		t.Fatalf("expected validation error on corrupted VIN check digit")
	}

	// 4. Garbage payload -> Parse error / DLQ trigger
	garbage := []byte(`{###MALFORMED_JSON###`)
	_, err = registry.DetectAndParse("", garbage)
	if err == nil {
		t.Fatalf("expected parse error on malformed payload")
	}

	// 5. Unknown OEM -> DLQ trigger
	unknownOEM := []byte(`{"oem": "UnknownMotorsX", "vin": "` + vin1 + `"}`)
	_, err = registry.DetectAndParse("", unknownOEM)
	if err == nil {
		t.Fatalf("expected error on unknown OEM")
	}
}

func TestCanonicalSerialization(t *testing.T) {
	vin := makeTestVIN("1VXEV0000AA000002")
	evt := &canonical.Event{
		SchemaV:   1,
		VIN:       vin,
		TS:        time.Date(2026, 9, 30, 10, 0, 0, 0, time.UTC),
		Seq:       42,
		OEM:       "VoltX",
		Lat:       37.7749,
		Lon:       -122.4194,
		Geohash7:  "9q8yyk8",
		SpeedKMH:  60.5,
		SOCPct:    80.0,
		OdoKM:     15000.0,
		BattTempC: 25.0,
		Charging:  0,
		ChargeKW:  0.0,
		DTC:       []string{"P0A1F"},
		Evt:       "NONE",
	}

	bytes, err := json.Marshal(evt)
	if err != nil {
		t.Fatalf("failed marshaling canonical event: %v", err)
	}

	var roundtrip canonical.Event
	if err := json.Unmarshal(bytes, &roundtrip); err != nil {
		t.Fatalf("failed unmarshaling canonical event: %v", err)
	}

	if roundtrip.VIN != evt.VIN || roundtrip.Seq != evt.Seq || roundtrip.Geohash7 != evt.Geohash7 {
		t.Errorf("roundtrip mismatch: expected %+v, got %+v", evt, roundtrip)
	}
}
