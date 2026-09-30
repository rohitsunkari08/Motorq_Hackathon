package battery_test

import (
	"testing"

	"github.com/rohitsunkari08/evc/services/simulator/pkg/battery"
)

func TestComputeSoH(t *testing.T) {
	// Fresh battery (0 EFC)
	freshSoH := battery.ComputeSoH(0, 0, 0, 0)
	if freshSoH != 1.0 {
		t.Errorf("expected 1.0 for fresh battery, got %f", freshSoH)
	}

	// 1 year low DC-fast: ~45 EFC, 15% DC-fast, 10 hot exposure
	// Calibrated target: ~1.5% degradation/year -> SoH ~ 0.984
	lowDCSoH := battery.ComputeSoH(45, 0.15, 10, 0)
	if lowDCSoH < 0.980 || lowDCSoH > 0.988 {
		t.Errorf("expected low DC-fast SoH ~ 0.980-0.988, got %f", lowDCSoH)
	}

	// 1 year heavy DC-fast: ~45 EFC, 65% DC-fast, 30 hot exposure
	// Calibrated target: ~3.0% degradation/year -> SoH ~ 0.970
	heavyDCSoH := battery.ComputeSoH(45, 0.65, 30, 0)
	if heavyDCSoH < 0.965 || heavyDCSoH > 0.975 {
		t.Errorf("expected heavy DC-fast SoH ~ 0.965-0.975, got %f", heavyDCSoH)
	}

	// Fleet mean: ~45 EFC, 35% DC-fast, 20 hot exposure -> ~2.2% degradation -> SoH ~ 0.978
	meanSoH := battery.ComputeSoH(45, 0.35, 20, 0)
	if meanSoH < 0.974 || meanSoH > 0.982 {
		t.Errorf("expected fleet mean SoH ~ 0.978, got %f", meanSoH)
	}

	if heavyDCSoH >= lowDCSoH {
		t.Errorf("heavy DC-fast should degrade faster than low DC-fast (%f >= %f)", heavyDCSoH, lowDCSoH)
	}
}
