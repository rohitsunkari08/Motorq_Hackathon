package alerts

import (
	"sync"
	"time"
)

type Debouncer struct {
	mu           sync.Mutex
	quietPeriod  time.Duration
	lastAlertMap map[string]time.Time // key: "vin:type"
}

func NewDebouncer(quietPeriod time.Duration) *Debouncer {
	if quietPeriod <= 0 {
		quietPeriod = 10 * time.Minute
	}
	return &Debouncer{
		quietPeriod:  quietPeriod,
		lastAlertMap: make(map[string]time.Time),
	}
}

// ShouldEmit checks if an alert for (vin, alertType) should be emitted.
// Returns true and updates the timestamp if allowed; returns false if within the debounce period.
func (d *Debouncer) ShouldEmit(vin string, alertType string, now time.Time) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	key := vin + ":" + alertType
	lastTime, exists := d.lastAlertMap[key]
	if exists && now.Sub(lastTime) < d.quietPeriod {
		return false
	}

	d.lastAlertMap[key] = now
	return true
}

// CleanStale removes entries older than 2x the quiet period to prevent memory growth
func (d *Debouncer) CleanStale(now time.Time) {
	d.mu.Lock()
	defer d.mu.Unlock()

	threshold := d.quietPeriod * 2
	for k, lastTime := range d.lastAlertMap {
		if now.Sub(lastTime) > threshold {
			delete(d.lastAlertMap, k)
		}
	}
}
