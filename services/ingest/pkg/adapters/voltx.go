package adapters

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
	"github.com/valyala/fastjson"
)

type VoltXAdapter struct{}

func (a *VoltXAdapter) OEM() string {
	return "VoltX"
}

func (a *VoltXAdapter) CanParse(raw []byte) bool {
	var p fastjson.Parser
	v, err := p.ParseBytes(raw)
	if err != nil {
		return false
	}
	oem := string(v.GetStringBytes("oem"))
	if oem == "VoltX" {
		return true
	}
	// Has standard VoltX snake_case keys
	return v.Exists("vin") && v.Exists("speed_kmh") && v.Exists("soc_pct")
}

type voltXPayload struct {
	VIN         string          `json:"vin"`
	TS          string          `json:"ts"`
	Seq         uint64          `json:"seq"`
	OEM         string          `json:"oem"`
	Lat         float64         `json:"lat"`
	Lon         float64         `json:"lon"`
	SpeedKMH    float64         `json:"speed_kmh"`
	SOCPct      float64         `json:"soc_pct"`
	OdoKM       float64         `json:"odo_km"`
	BattTempC   float64         `json:"batt_temp_c"`
	Charging    json.RawMessage `json:"charging"`
	ChargeKW    float64         `json:"charge_kw"`
	DTC         []string        `json:"dtc"`
	Evt         string          `json:"evt"`
}

func (a *VoltXAdapter) Parse(raw []byte) (*canonical.Event, error) {
	var payload voltXPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("voltx json parse error: %w", err)
	}

	if payload.VIN == "" {
		return nil, fmt.Errorf("voltx missing vin")
	}

	t, err := time.Parse(time.RFC3339, payload.TS)
	if err != nil {
		t, err = time.Parse("2006-01-02T15:04:05.999999999Z07:00", payload.TS)
		if err != nil {
			return nil, fmt.Errorf("voltx invalid ts '%s': %w", payload.TS, err)
		}
	}

	chargingInt := 0
	if len(payload.Charging) > 0 {
		var b bool
		if err := json.Unmarshal(payload.Charging, &b); err == nil {
			if b {
				chargingInt = 1
			}
		} else {
			var i int
			if err := json.Unmarshal(payload.Charging, &i); err == nil {
				chargingInt = i
			}
		}
	}

	evt := payload.Evt
	if evt == "" {
		evt = "NONE"
	}
	if payload.DTC == nil {
		payload.DTC = []string{}
	}

	event := &canonical.Event{
		SchemaV:   1,
		VIN:       payload.VIN,
		TS:        t.UTC(),
		Seq:       payload.Seq,
		OEM:       a.OEM(),
		Lat:       payload.Lat,
		Lon:       payload.Lon,
		SpeedKMH:  payload.SpeedKMH,
		SOCPct:    payload.SOCPct,
		OdoKM:     payload.OdoKM,
		BattTempC: payload.BattTempC,
		Charging:  chargingInt,
		ChargeKW:  payload.ChargeKW,
		DTC:       payload.DTC,
		Evt:       evt,
	}
	event.PopulateGeohash()

	return event, nil
}
