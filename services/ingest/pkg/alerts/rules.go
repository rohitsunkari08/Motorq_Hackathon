package alerts

import (
	"context"
	"fmt"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
)

// Alert types
const (
	TypeRangeRisk  = "RANGE_RISK"
	TypeLowSOC     = "LOW_SOC"
	TypeThermal    = "THERMAL"
	TypeRapidDrop  = "RAPID_DROP"
	TypeHarshBrake = "HARSH_BRAKE"
)

// Alert severities matching Postgres alert.severity SMALLINT
const (
	SeverityCritical = "CRITICAL" // 1
	SeverityHigh     = "HIGH"     // 2
	SeverityWarn     = "WARN"     // 3
	SeverityInfo     = "INFO"     // 4

	LevelCritical = 1
	LevelHigh     = 2
	LevelWarn     = 3
	LevelInfo     = 4
)

type AlertEvent struct {
	AlertID       string                 `json:"alert_id"`
	VIN           string                 `json:"vin"`
	Type          string                 `json:"type"`
	Severity      string                 `json:"severity"`
	SeverityLevel int                    `json:"severity_level"`
	EventTS       string                 `json:"event_ts"`
	EmitTS        string                 `json:"emit_ts"`
	LatencyMS     float64                `json:"latency_ms"`
	Lat           float64                `json:"lat"`
	Lon           float64                `json:"lon"`
	Detail        map[string]interface{} `json:"detail"`
}

type RuleEngine struct {
	chargers *ChargerIndex
	params   *VehicleParamsStore
	windows  *WindowManager
}

func NewRuleEngine(chargers *ChargerIndex, params *VehicleParamsStore, windows *WindowManager) *RuleEngine {
	return &RuleEngine{
		chargers: chargers,
		params:   params,
		windows:  windows,
	}
}

// EvaluateRules evaluates all 5 canonical alert rules for an incoming event
func (re *RuleEngine) EvaluateRules(ctx context.Context, ev *canonical.Event) []*AlertEvent {
	alerts := make([]*AlertEvent, 0)
	now := time.Now().UTC()
	window := re.windows.GetOrCreate(ev.VIN)
	window.Add(ev)

	// 1. RANGE_RISK: predicted_range = (soc/100) * capacity * soh / eff_kwh_per_km < 1.2 * dist_to_nearest_charger
	// Only evaluate if not actively charging and vehicle has valid coordinates
	if ev.Charging == 0 && (ev.Lat != 0 || ev.Lon != 0) {
		p := re.params.Get(ctx, ev.VIN)
		if p.EffKWHPerKM > 0 && p.CapacityKWH > 0 {
			predictedRangeKM := (ev.SOCPct / 100.0) * p.CapacityKWH * p.SOH / p.EffKWHPerKM

			if charger, distKM, ok := re.chargers.NearestCharger(ev.Lat, ev.Lon); ok {
				if predictedRangeKM < 1.2*distKM {
					alerts = append(alerts, &AlertEvent{
						AlertID:       fmt.Sprintf("%s-%d-RANGE_RISK", ev.VIN, ev.TS.UnixMilli()),
						VIN:           ev.VIN,
						Type:          TypeRangeRisk,
						Severity:      SeverityCritical,
						SeverityLevel: LevelCritical,
						EventTS:       ev.TS.UTC().Format(time.RFC3339),
						EmitTS:        now.Format(time.RFC3339Nano),
						LatencyMS:     float64(now.Sub(ev.TS).Milliseconds()),
						Lat:           ev.Lat,
						Lon:           ev.Lon,
						Detail: map[string]interface{}{
							"predicted_range_km":      predictedRangeKM,
							"nearest_charger_dist_km": distKM,
							"nearest_charger_id":      charger.ID,
							"nearest_charger_network": charger.Network,
							"soc_pct":                 ev.SOCPct,
							"battery_capacity_kwh":    p.CapacityKWH,
						},
					})
				}
			}
		}
	}

	// 2. LOW_SOC: soc_pct < 15.0
	if ev.SOCPct < 15.0 {
		alerts = append(alerts, &AlertEvent{
			AlertID:       fmt.Sprintf("%s-%d-LOW_SOC", ev.VIN, ev.TS.UnixMilli()),
			VIN:           ev.VIN,
			Type:          TypeLowSOC,
			Severity:      SeverityWarn,
			SeverityLevel: LevelWarn,
			EventTS:       ev.TS.UTC().Format(time.RFC3339),
			EmitTS:        now.Format(time.RFC3339Nano),
			LatencyMS:     float64(now.Sub(ev.TS).Milliseconds()),
			Lat:           ev.Lat,
			Lon:           ev.Lon,
			Detail: map[string]interface{}{
				"soc_pct":   ev.SOCPct,
				"threshold": 15.0,
			},
		})
	}

	// 3. THERMAL: temp > 50C for 60s
	if isThermal, maxTemp, sustainedSec := window.CheckThermal(60*time.Second, 50.0); isThermal {
		alerts = append(alerts, &AlertEvent{
			AlertID:       fmt.Sprintf("%s-%d-THERMAL", ev.VIN, ev.TS.UnixMilli()),
			VIN:           ev.VIN,
			Type:          TypeThermal,
			Severity:      SeverityHigh,
			SeverityLevel: LevelHigh,
			EventTS:       ev.TS.UTC().Format(time.RFC3339),
			EmitTS:        now.Format(time.RFC3339Nano),
			LatencyMS:     float64(now.Sub(ev.TS).Milliseconds()),
			Lat:           ev.Lat,
			Lon:           ev.Lon,
			Detail: map[string]interface{}{
				"batt_temp_c":   ev.BattTempC,
				"max_temp_c":    maxTemp,
				"sustained_sec": sustainedSec,
				"threshold_c":   50.0,
			},
		})
	}

	// 4. RAPID_DROP: soc drop > 8% in 5 min while speed < 30 km/h
	if isRapidDrop, dropPct, speed := window.CheckRapidDrop(8.0, 30.0); isRapidDrop {
		alerts = append(alerts, &AlertEvent{
			AlertID:       fmt.Sprintf("%s-%d-RAPID_DROP", ev.VIN, ev.TS.UnixMilli()),
			VIN:           ev.VIN,
			Type:          TypeRapidDrop,
			Severity:      SeverityWarn,
			SeverityLevel: LevelWarn,
			EventTS:       ev.TS.UTC().Format(time.RFC3339),
			EmitTS:        now.Format(time.RFC3339Nano),
			LatencyMS:     float64(now.Sub(ev.TS).Milliseconds()),
			Lat:           ev.Lat,
			Lon:           ev.Lon,
			Detail: map[string]interface{}{
				"soc_drop_pct": dropPct,
				"speed_kmh":    speed,
				"current_soc":  ev.SOCPct,
			},
		})
	}

	// 5. HARSH_BRAKE: evt == "HARSH_BRAKE"
	if ev.Evt == "HARSH_BRAKE" {
		alerts = append(alerts, &AlertEvent{
			AlertID:       fmt.Sprintf("%s-%d-HARSH_BRAKE", ev.VIN, ev.TS.UnixMilli()),
			VIN:           ev.VIN,
			Type:          TypeHarshBrake,
			Severity:      SeverityInfo,
			SeverityLevel: LevelInfo,
			EventTS:       ev.TS.UTC().Format(time.RFC3339),
			EmitTS:        now.Format(time.RFC3339Nano),
			LatencyMS:     float64(now.Sub(ev.TS).Milliseconds()),
			Lat:           ev.Lat,
			Lon:           ev.Lon,
			Detail: map[string]interface{}{
				"speed_kmh": ev.SpeedKMH,
				"evt":       ev.Evt,
			},
		})
	}

	return alerts
}
