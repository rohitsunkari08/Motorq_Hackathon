package adapters

import (
	"encoding/json"
	"fmt"
	"math"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
	"github.com/valyala/fastjson"
)

type NordMotorsAdapter struct{}

func (a *NordMotorsAdapter) OEM() string {
	return "NordMotors"
}

func (a *NordMotorsAdapter) CanParse(raw []byte) bool {
	var p fastjson.Parser
	v, err := p.ParseBytes(raw)
	if err != nil {
		return false
	}
	if string(v.GetStringBytes("oem")) == "NordMotors" {
		return true
	}
	return v.Exists("vehicle") && v.Exists("position") && v.Exists("battery")
}

type nordMotorsPayload struct {
	OEM      string `json:"oem"`
	Vehicle  struct {
		ID string `json:"id"`
	} `json:"vehicle"`
	Position struct {
		Latitude  float64 `json:"latitude"`
		Longitude float64 `json:"longitude"`
	} `json:"position"`
	Battery struct {
		Level float64 `json:"level"` // 0.0 - 1.0
		TempF float64 `json:"tempF"` // Fahrenheit
	} `json:"battery"`
	SpeedMph  float64  `json:"speedMph"`
	OdoMiles  float64  `json:"odoMiles"`
	Charging  bool     `json:"charging"`
	ChargeKw  float64  `json:"chargeKw"`
	DTCs      []string `json:"dtcs"`
	Event     string   `json:"event"`
	Seq       uint64   `json:"seq"`
	Time      string   `json:"time"`
}

func (a *NordMotorsAdapter) Parse(raw []byte) (*canonical.Event, error) {
	var p nordMotorsPayload
	if err := json.Unmarshal(raw, &p); err != nil {
		return nil, fmt.Errorf("nordmotors json parse error: %w", err)
	}

	vin := p.Vehicle.ID
	if vin == "" {
		return nil, fmt.Errorf("nordmotors missing vehicle.id")
	}

	t, err := time.Parse(time.RFC3339, p.Time)
	if err != nil {
		t, err = time.Parse("2006-01-02T15:04:05.999999999Z07:00", p.Time)
		if err != nil {
			return nil, fmt.Errorf("nordmotors invalid time '%s': %w", p.Time, err)
		}
	}

	// Conversions
	speedKMH := math.Round(p.SpeedMph*1.609344*100) / 100
	odoKM := math.Round(p.OdoMiles*1.609344*100) / 100
	socPct := p.Battery.Level
	if socPct <= 1.0 {
		socPct = socPct * 100.0
	}
	socPct = math.Round(socPct*100) / 100

	battTempC := math.Round(((p.Battery.TempF-32.0)*5.0/9.0)*100) / 100

	chargingInt := 0
	if p.Charging {
		chargingInt = 1
	}

	evt := p.Event
	if evt == "" {
		evt = "NONE"
	}
	if p.DTCs == nil {
		p.DTCs = []string{}
	}

	event := &canonical.Event{
		SchemaV:   1,
		VIN:       vin,
		TS:        t.UTC(),
		Seq:       p.Seq,
		OEM:       a.OEM(),
		Lat:       p.Position.Latitude,
		Lon:       p.Position.Longitude,
		SpeedKMH:  speedKMH,
		SOCPct:    socPct,
		OdoKM:     odoKM,
		BattTempC: battTempC,
		Charging:  chargingInt,
		ChargeKW:  p.ChargeKw,
		DTC:       p.DTCs,
		Evt:       evt,
	}
	event.PopulateGeohash()

	return event, nil
}
