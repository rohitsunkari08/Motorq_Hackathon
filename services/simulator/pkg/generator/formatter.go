package generator

import (
	"encoding/json"
	"fmt"
	"math"
	"math/rand"
	"strings"
	"time"

	"github.com/rohitsunkari08/evc/services/simulator/pkg/vehicles"
)

type Formatter struct {
	rnd *rand.Rand
}

func NewFormatter(seed int64) *Formatter {
	return &Formatter{
		rnd: rand.New(rand.NewSource(seed)),
	}
}

type PayloadResult struct {
	OEM         string
	VIN         string
	Payload     []byte
	IsDuplicate bool
	IsGarbage   bool
}

// FormatEvent produces the OEM-specific raw payload according to NOTE.md §5.2 and §5.3.
func (f *Formatter) FormatEvent(v *vehicles.VehicleState, ts time.Time, injectNoise bool) PayloadResult {
	res := PayloadResult{
		OEM: v.OEM,
		VIN: v.VIN,
	}

	eventTS := ts
	vinToUse := v.VIN

	// Occasional realistic dirty data if enabled
	if injectNoise {
		roll := f.rnd.Float64()
		if roll < 0.001 {
			// 0.1% bad VIN / garbage payload
			res.IsGarbage = true
			if f.rnd.Float64() < 0.5 {
				vinToUse = vehicles.GenerateCorruptedVIN(v.OEM, v.Index+1)
			} else {
				res.Payload = []byte(`{"corrupted": true, "raw": "###GARBAGE_PAYLOAD###"}`)
				return res
			}
		} else if roll < 0.021 {
			// ~2% out-of-order jitter up to 30s
			jitterSecs := 5 + f.rnd.Intn(25)
			eventTS = eventTS.Add(-time.Duration(jitterSecs) * time.Second)
		}
	}

	switch v.OEM {
	case "VoltX":
		res.Payload = f.formatVoltX(v, vinToUse, eventTS)
	case "NordMotors":
		res.Payload = f.formatNordMotors(v, vinToUse, eventTS)
	case "AsiaDrive":
		res.Payload = f.formatAsiaDrive(v, vinToUse, eventTS)
	case "EuroEV":
		res.Payload = f.formatEuroEV(v, vinToUse, eventTS)
	case "ZephyrEV":
		res.Payload = f.formatZephyrEV(v, vinToUse, eventTS)
	default:
		res.Payload = f.formatVoltX(v, vinToUse, eventTS)
	}

	return res
}

func (f *Formatter) formatVoltX(v *vehicles.VehicleState, vin string, ts time.Time) []byte {
	dtcs := v.DTCs
	if dtcs == nil {
		dtcs = []string{}
	}
	m := map[string]interface{}{
		"oem":         "VoltX",
		"vin":         vin,
		"ts":          ts.UTC().Format(time.RFC3339),
		"seq":         v.Seq,
		"lat":         v.Lat,
		"lon":         v.Lon,
		"speed_kmh":   v.SpeedKMH,
		"soc_pct":     v.SOCPct,
		"odo_km":      v.OdoKM,
		"batt_temp_c": v.BattTempC,
		"charging":    v.Charging,
		"charge_kw":   v.ChargeKW,
		"dtc":         dtcs,
		"evt":         v.LastEvt,
	}
	b, _ := json.Marshal(m)
	return b
}

func (f *Formatter) formatNordMotors(v *vehicles.VehicleState, vin string, ts time.Time) []byte {
	// NordMotors: nested JSON camelCase, mph, miles, tempF, soc fraction 0.0-1.0
	speedMph := math.Round((v.SpeedKMH/1.609344)*10) / 10
	odoMiles := math.Round((v.OdoKM/1.609344)*10) / 10
	tempF := math.Round((v.BattTempC*9.0/5.0+32.0)*10) / 10
	level := math.Round((v.SOCPct/100.0)*1000) / 1000

	dtcs := v.DTCs
	if dtcs == nil {
		dtcs = []string{}
	}

	m := map[string]interface{}{
		"oem": "NordMotors",
		"vehicle": map[string]interface{}{
			"id": vin,
		},
		"position": map[string]interface{}{
			"latitude":  v.Lat,
			"longitude": v.Lon,
		},
		"battery": map[string]interface{}{
			"level": level,
			"tempF": tempF,
		},
		"speedMph": speedMph,
		"odoMiles": odoMiles,
		"charging": v.Charging == 1,
		"chargeKw": v.ChargeKW,
		"dtcs":     dtcs,
		"event":    v.LastEvt,
		"seq":      v.Seq,
		"time":     ts.UTC().Format(time.RFC3339),
	}
	b, _ := json.Marshal(m)
	return b
}

func (f *Formatter) formatAsiaDrive(v *vehicles.VehicleState, vin string, ts time.Time) []byte {
	// AsiaDrive: pipe-delimited string VIN|epoch_ms|lat|lon|kmh|soc|odo|tempC|chg_kw|DTCs;seq;evt
	dtcStr := strings.Join(v.DTCs, ",")
	s := fmt.Sprintf("%s|%d|%.5f|%.5f|%.1f|%.1f|%.1f|%.1f|%.1f|%s;%d;%s",
		vin,
		ts.UTC().UnixMilli(),
		v.Lat,
		v.Lon,
		v.SpeedKMH,
		v.SOCPct,
		v.OdoKM,
		v.BattTempC,
		v.ChargeKW,
		dtcStr,
		v.Seq,
		v.LastEvt,
	)
	return []byte(s)
}

func (f *Formatter) formatEuroEV(v *vehicles.VehicleState, vin string, ts time.Time) []byte {
	// EuroEV: signals array, epoch seconds
	signals := []map[string]interface{}{
		{"name": "lat", "value": v.Lat, "unit": "deg"},
		{"name": "lon", "value": v.Lon, "unit": "deg"},
		{"name": "speed", "value": v.SpeedKMH, "unit": "km/h"},
		{"name": "soc", "value": v.SOCPct, "unit": "pct"},
		{"name": "odo", "value": v.OdoKM, "unit": "km"},
		{"name": "temp", "value": v.BattTempC, "unit": "c"},
		{"name": "charging", "value": v.Charging, "unit": ""},
		{"name": "charge_kw", "value": v.ChargeKW, "unit": "kw"},
		{"name": "evt", "value": v.LastEvt, "unit": ""},
	}
	if len(v.DTCs) > 0 {
		signals = append(signals, map[string]interface{}{
			"name": "dtc", "value": v.DTCs[0], "unit": "",
		})
	}

	m := map[string]interface{}{
		"oem":       "EuroEV",
		"vin":       vin,
		"timestamp": ts.UTC().Unix(),
		"seq":       v.Seq,
		"signals":   signals,
	}
	b, _ := json.Marshal(m)
	return b
}

func (f *Formatter) formatZephyrEV(v *vehicles.VehicleState, vin string, ts time.Time) []byte {
	// ZephyrEV: short keys, permille soc (0-1000)
	socPM := math.Round(v.SOCPct * 10)
	dtcs := v.DTCs
	if dtcs == nil {
		dtcs = []string{}
	}

	m := map[string]interface{}{
		"oem": "ZephyrEV",
		"v":   vin,
		"t":   ts.UTC().UnixMilli(),
		"sq":  v.Seq,
		"pos": map[string]interface{}{
			"lat": v.Lat,
			"lon": v.Lon,
		},
		"spd":    v.SpeedKMH,
		"soc_pm": socPM,
		"odo":    v.OdoKM,
		"tmp":    v.BattTempC,
		"chg":    v.Charging,
		"pwr":    v.ChargeKW,
		"dtc":    dtcs,
		"evt":    v.LastEvt,
	}
	b, _ := json.Marshal(m)
	return b
}
