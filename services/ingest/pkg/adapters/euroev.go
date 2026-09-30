package adapters

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
	"github.com/valyala/fastjson"
)

type EuroEVAdapter struct{}

func (a *EuroEVAdapter) OEM() string {
	return "EuroEV"
}

func (a *EuroEVAdapter) CanParse(raw []byte) bool {
	var p fastjson.Parser
	v, err := p.ParseBytes(raw)
	if err != nil {
		return false
	}
	if string(v.GetStringBytes("oem")) == "EuroEV" {
		return true
	}
	return v.Exists("signals") && v.Exists("vin")
}

type euroEVSignal struct {
	Name  string          `json:"name"`
	Value json.RawMessage `json:"value"`
	Unit  string          `json:"unit"`
}

type euroEVPayload struct {
	OEM       string         `json:"oem"`
	VIN       string         `json:"vin"`
	Timestamp int64          `json:"timestamp"` // epoch seconds
	Seq       uint64         `json:"seq"`
	Signals   []euroEVSignal `json:"signals"`
}

func (a *EuroEVAdapter) Parse(raw []byte) (*canonical.Event, error) {
	var p euroEVPayload
	if err := json.Unmarshal(raw, &p); err != nil {
		return nil, fmt.Errorf("euroev json parse error: %w", err)
	}

	if p.VIN == "" {
		return nil, fmt.Errorf("euroev missing vin")
	}

	t := time.Unix(p.Timestamp, 0).UTC()

	event := &canonical.Event{
		SchemaV: 1,
		VIN:     p.VIN,
		TS:      t,
		Seq:     p.Seq,
		OEM:     a.OEM(),
		DTC:     []string{},
		Evt:     "NONE",
	}

	for _, sig := range p.Signals {
		name := strings.ToLower(sig.Name)
		valStr := strings.Trim(string(sig.Value), `"`)

		switch name {
		case "lat", "latitude":
			if f, err := strconv.ParseFloat(valStr, 64); err == nil {
				event.Lat = f
			}
		case "lon", "longitude":
			if f, err := strconv.ParseFloat(valStr, 64); err == nil {
				event.Lon = f
			}
		case "speed", "speed_kmh":
			if f, err := strconv.ParseFloat(valStr, 64); err == nil {
				event.SpeedKMH = f
			}
		case "soc", "soc_pct":
			if f, err := strconv.ParseFloat(valStr, 64); err == nil {
				event.SOCPct = f
			}
		case "odo", "odo_km", "odometer":
			if f, err := strconv.ParseFloat(valStr, 64); err == nil {
				event.OdoKM = f
			}
		case "temp", "batt_temp", "battery_temp", "temp_c":
			if f, err := strconv.ParseFloat(valStr, 64); err == nil {
				event.BattTempC = f
			}
		case "charging", "is_charging":
			if valStr == "true" || valStr == "1" {
				event.Charging = 1
			} else {
				event.Charging = 0
			}
		case "charge_kw", "charge_power", "chg_kw":
			if f, err := strconv.ParseFloat(valStr, 64); err == nil {
				event.ChargeKW = f
			}
		case "dtc", "trouble_code":
			if valStr != "" && valStr != "null" {
				// Can be single DTC or comma-separated or json array
				var arr []string
				if err := json.Unmarshal(sig.Value, &arr); err == nil {
					event.DTC = append(event.DTC, arr...)
				} else {
					for _, d := range strings.Split(valStr, ",") {
						d = strings.TrimSpace(d)
						if d != "" {
							event.DTC = append(event.DTC, d)
						}
					}
				}
			}
		case "evt", "event", "event_type":
			if valStr != "" && valStr != "null" {
				event.Evt = valStr
			}
		}
	}

	event.PopulateGeohash()
	return event, nil
}
