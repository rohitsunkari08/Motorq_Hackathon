package alerts

import (
	"sync"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
)

type TelemetrySnapshot struct {
	TS        time.Time
	Lat       float64
	Lon       float64
	SOCPct    float64
	SpeedKMH  float64
	BattTempC float64
	Evt       string
}

type VehicleWindow struct {
	mu        sync.Mutex
	snapshots []TelemetrySnapshot
}

func NewVehicleWindow() *VehicleWindow {
	return &VehicleWindow{
		snapshots: make([]TelemetrySnapshot, 0, 32),
	}
}

func (vw *VehicleWindow) Add(ev *canonical.Event) {
	vw.mu.Lock()
	defer vw.mu.Unlock()

	snap := TelemetrySnapshot{
		TS:        ev.TS.UTC(),
		Lat:       ev.Lat,
		Lon:       ev.Lon,
		SOCPct:    ev.SOCPct,
		SpeedKMH:  ev.SpeedKMH,
		BattTempC: ev.BattTempC,
		Evt:       ev.Evt,
	}

	vw.snapshots = append(vw.snapshots, snap)

	// Prune snapshots older than 5 minutes from the latest event timestamp
	cutoff := snap.TS.Add(-5 * time.Minute)
	startIdx := 0
	for startIdx < len(vw.snapshots) && vw.snapshots[startIdx].TS.Before(cutoff) {
		startIdx++
	}
	if startIdx > 0 {
		vw.snapshots = append([]TelemetrySnapshot(nil), vw.snapshots[startIdx:]...)
	}
}

// CheckThermal checks if temperature has been > threshold (50C) for duration (60s)
func (vw *VehicleWindow) CheckThermal(duration time.Duration, threshold float64) (bool, float64, float64) {
	vw.mu.Lock()
	defer vw.mu.Unlock()

	n := len(vw.snapshots)
	if n == 0 {
		return false, 0, 0
	}

	latest := vw.snapshots[n-1]
	if latest.BattTempC <= threshold {
		return false, 0, 0
	}

	// Trace backwards while temperature is strictly above threshold
	earliestHigh := latest.TS
	maxTemp := latest.BattTempC
	for i := n - 1; i >= 0; i-- {
		s := vw.snapshots[i]
		if s.BattTempC > maxTemp {
			maxTemp = s.BattTempC
		}
		if s.BattTempC > threshold {
			earliestHigh = s.TS
		} else {
			break
		}
	}

	sustainedDuration := latest.TS.Sub(earliestHigh)
	if sustainedDuration >= duration {
		return true, maxTemp, sustainedDuration.Seconds()
	}

	return false, maxTemp, sustainedDuration.Seconds()
}

// CheckRapidDrop checks if SOC has dropped by > dropThreshold (8%) in the window while speed < maxSpeed (30 km/h)
func (vw *VehicleWindow) CheckRapidDrop(dropThreshold float64, maxSpeed float64) (bool, float64, float64) {
	vw.mu.Lock()
	defer vw.mu.Unlock()

	n := len(vw.snapshots)
	if n < 2 {
		return false, 0, 0
	}

	latest := vw.snapshots[n-1]
	if latest.SpeedKMH >= maxSpeed {
		return false, 0, 0
	}

	// Find maximum SOC prior to current event
	maxSOC := latest.SOCPct
	for i := 0; i < n-1; i++ {
		if vw.snapshots[i].SOCPct > maxSOC {
			maxSOC = vw.snapshots[i].SOCPct
		}
	}

	drop := maxSOC - latest.SOCPct
	if drop > dropThreshold {
		return true, drop, latest.SpeedKMH
	}

	return false, drop, latest.SpeedKMH
}

// WindowManager manages sliding windows for all active vehicles
type WindowManager struct {
	mu      sync.RWMutex
	windows map[string]*VehicleWindow
}

func NewWindowManager() *WindowManager {
	return &WindowManager{
		windows: make(map[string]*VehicleWindow),
	}
}

func (wm *WindowManager) GetOrCreate(vin string) *VehicleWindow {
	wm.mu.RLock()
	w, exists := wm.windows[vin]
	wm.mu.RUnlock()

	if exists {
		return w
	}

	wm.mu.Lock()
	defer wm.mu.Unlock()
	if w, exists = wm.windows[vin]; exists {
		return w
	}

	w = NewVehicleWindow()
	wm.windows[vin] = w
	return w
}
