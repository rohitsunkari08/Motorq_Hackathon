package canonical

import (
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/mmcloughlin/geohash"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/validation"
)

// Event represents the canonical telemetry event (schema_v: 1)
type Event struct {
	SchemaV   int       `json:"schema_v"`
	VIN       string    `json:"vin"`
	TS        time.Time `json:"ts"`
	Seq       uint64    `json:"seq"`
	OEM       string    `json:"oem"`
	Lat       float64   `json:"lat"`
	Lon       float64   `json:"lon"`
	Geohash7  string    `json:"geohash7"`
	SpeedKMH  float64   `json:"speed_kmh"`
	SOCPct    float64   `json:"soc_pct"`
	OdoKM     float64   `json:"odo_km"`
	BattTempC float64   `json:"batt_temp_c"`
	Charging  int       `json:"charging"` // 0 or 1
	ChargeKW  float64   `json:"charge_kw"`
	DTC       []string  `json:"dtc"`
	Evt       string    `json:"evt"`
}

// Custom JSON marshaling for UTC ISO 8601 timestamps
func (e Event) MarshalJSON() ([]byte, error) {
	type Alias Event
	return json.Marshal(&struct {
		Alias
		TS string `json:"ts"`
	}{
		Alias: (Alias)(e),
		TS:    e.TS.UTC().Format(time.RFC3339),
	})
}

func (e *Event) UnmarshalJSON(data []byte) error {
	type Alias Event
	aux := &struct {
		*Alias
		TS string `json:"ts"`
	}{
		Alias: (*Alias)(e),
	}
	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}
	t, err := time.Parse(time.RFC3339, aux.TS)
	if err != nil {
		// Try fallback ISO formats
		t, err = time.Parse("2006-01-02T15:04:05.999999999Z07:00", aux.TS)
		if err != nil {
			return fmt.Errorf("invalid timestamp format: %w", err)
		}
	}
	e.TS = t.UTC()
	return nil
}

// PopulateGeohash computes geohash7 if lat/lon are valid and geohash7 is not already populated.
func (e *Event) PopulateGeohash() {
	if e.Geohash7 == "" && e.Lat >= -90.0 && e.Lat <= 90.0 && e.Lon >= -180.0 && e.Lon <= 180.0 {
		e.Geohash7 = geohash.EncodeWithPrecision(e.Lat, e.Lon, 7)
	}
}

// Validate checks all schema constraints per NOTE.md §5.1.
func (e *Event) Validate() error {
	if e.SchemaV != 1 {
		return errors.New("unsupported schema_v: expected 1")
	}
	if err := validation.ValidateVIN(e.VIN); err != nil {
		return fmt.Errorf("vin validation failed: %w", err)
	}
	if err := validation.ValidateRanges(e.SOCPct, e.SpeedKMH, e.BattTempC, e.Lat, e.Lon, e.TS); err != nil {
		return fmt.Errorf("range validation failed: %w", err)
	}
	if err := validation.ValidateDTCs(e.DTC); err != nil {
		return fmt.Errorf("dtc validation failed: %w", err)
	}
	if err := validation.ValidateEvent(e.Evt); err != nil {
		return fmt.Errorf("evt validation failed: %w", err)
	}
	if e.Charging != 0 && e.Charging != 1 {
		return errors.New("charging status must be 0 or 1")
	}
	if e.ChargeKW < 0 {
		return errors.New("charge_kw must be non-negative")
	}
	if e.OdoKM < 0 {
		return errors.New("odo_km must be non-negative")
	}
	return nil
}
