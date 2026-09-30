package adapters

import (
	"encoding/json"
	"fmt"
	"math"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
	"github.com/valyala/fastjson"
)

type ZephyrEVAdapter struct{}

func (a *ZephyrEVAdapter) OEM() string {
	return "ZephyrEV"
}

func (a *ZephyrEVAdapter) CanParse(raw []byte) bool {
	var p fastjson.Parser
	v, err := p.ParseBytes(raw)
	if err != nil {
		return false
	}
	if string(v.GetStringBytes("oem")) == "ZephyrEV" {
		return true
	}
	return v.Exists("v") && v.Exists("soc_pm") && v.Exists("pos")
}

type zephyrEVPayload struct {
	OEM   string `json:"oem"`
	V     string `json:"v"`  // VIN
	T     int64  `json:"t"`  // epoch_ms
	Sq    uint64 `json:"sq"` // seq
	Pos   struct {
		Lat float64 `json:"lat"`
		Lon float64 `json:"lon"`
	} `json:"pos"`
	Spd   float64  `json:"spd"`
	SocPM float64  `json:"soc_pm"` // permille 0 - 1000
	Odo   float64  `json:"odo"`
	Tmp   float64  `json:"tmp"`
	Chg   int      `json:"chg"`
	Pwr   float64  `json:"pwr"`
	DTC   []string `json:"dtc"`
	Evt   string   `json:"evt"`
}

func (a *ZephyrEVAdapter) Parse(raw []byte) (*canonical.Event, error) {
	var p zephyrEVPayload
	if err := json.Unmarshal(raw, &p); err != nil {
		return nil, fmt.Errorf("zephyrev json parse error: %w", err)
	}

	if p.V == "" {
		return nil, fmt.Errorf("zephyrev missing vin (v)")
	}

	t := time.UnixMilli(p.T).UTC()
	socPct := math.Round((p.SocPM/10.0)*100) / 100 // 825 -> 82.5

	evt := p.Evt
	if evt == "" {
		evt = "NONE"
	}
	if p.DTC == nil {
		p.DTC = []string{}
	}

	event := &canonical.Event{
		SchemaV:   1,
		VIN:       p.V,
		TS:        t,
		Seq:       p.Sq,
		OEM:       a.OEM(),
		Lat:       p.Pos.Lat,
		Lon:       p.Pos.Lon,
		SpeedKMH:  p.Spd,
		SOCPct:    socPct,
		OdoKM:     p.Odo,
		BattTempC: p.Tmp,
		Charging:  p.Chg,
		ChargeKW:  p.Pwr,
		DTC:       p.DTC,
		Evt:       evt,
	}
	event.PopulateGeohash()

	return event, nil
}
