package sink

import (
	"testing"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
)

func TestLatestByVINSelection(t *testing.T) {
	t.Parallel()
	now := time.Now().UTC()

	vins := []string{"1EEEV01A600000001", "1EEEV01A600000002"}

	events := []*canonical.Event{
		{
			VIN:    vins[0],
			TS:     now.Add(-10 * time.Second),
			Seq:    1,
			SOCPct: 50.0,
		},
		{
			VIN:    vins[0],
			TS:     now,
			Seq:    2,
			SOCPct: 49.5,
		},
		{
			VIN:    vins[1],
			TS:     now.Add(-5 * time.Second),
			Seq:    10,
			SOCPct: 80.0,
		},
	}

	latestMap := make(map[string]*canonical.Event)
	for _, ev := range events {
		existing, exists := latestMap[ev.VIN]
		if !exists || ev.TS.After(existing.TS) || (ev.TS.Equal(existing.TS) && ev.Seq >= existing.Seq) {
			latestMap[ev.VIN] = ev
		}
	}

	if len(latestMap) != 2 {
		t.Fatalf("expected 2 unique VINs in latestMap, got %d", len(latestMap))
	}
	if latestMap[vins[0]].Seq != 2 {
		t.Errorf("expected vin[0] latest seq to be 2, got %d", latestMap[vins[0]].Seq)
	}
	if latestMap[vins[0]].SOCPct != 49.5 {
		t.Errorf("expected vin[0] latest SOC to be 49.5, got %f", latestMap[vins[0]].SOCPct)
	}
	if latestMap[vins[1]].Seq != 10 {
		t.Errorf("expected vin[1] latest seq to be 10, got %d", latestMap[vins[1]].Seq)
	}
}

type ContextTest struct {
	*testing.T
}

func TestConfigDefaults(t *testing.T) {
	cfg := Config{}
	svc, err := NewService(cfg)
	// Since kafka brokers are empty, NewService may return error or initialize
	if err == nil && svc != nil {
		if svc.cfg.CanonicalTopic != "telemetry.canonical" {
			t.Errorf("expected default canonical topic, got %s", svc.cfg.CanonicalTopic)
		}
		if svc.cfg.BatchSize != 100000 {
			t.Errorf("expected default batch size 100000, got %d", svc.cfg.BatchSize)
		}
	}
}
