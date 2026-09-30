package vehicles_test

import (
	"testing"

	"github.com/rohitsunkari08/evc/services/simulator/pkg/vehicles"
)

func TestNewFleet(t *testing.T) {
	// Create fleet of 100,000 vehicles (per §5.3)
	fleet := vehicles.NewFleet(100_000, 42)
	if fleet.Size() != 100_000 {
		t.Fatalf("expected fleet size 100000, got %d", fleet.Size())
	}

	// Verify sample vehicles across the fleet
	sampleIndices := []int{0, 1000, 25000, 50000, 99999}
	for _, idx := range sampleIndices {
		v := fleet.GetVehicle(idx)
		if v.VIN == "" || len(v.VIN) != 17 {
			t.Errorf("vehicle %d has invalid vin %s", idx, v.VIN)
		}
		if v.OEM == "" {
			t.Errorf("vehicle %d missing OEM", idx)
		}
		if v.TrueSOH < 0.65 || v.TrueSOH > 1.0 {
			t.Errorf("vehicle %d true SOH out of bounds: %f", idx, v.TrueSOH)
		}
		if v.Model.CapacityKWh < 40.0 || v.Model.CapacityKWh > 100.0 {
			t.Errorf("vehicle %d battery capacity out of range: %f", idx, v.Model.CapacityKWh)
		}
	}
}

func TestFleetStepPhysics(t *testing.T) {
	fleet := vehicles.NewFleet(10, 42)
	v := fleet.GetVehicle(0)

	initialOdo := v.OdoKM
	initialSeq := v.Seq

	// Simulate 10 driving steps
	for i := 0; i < 10; i++ {
		fleet.Step(v, 1.0)
	}

	if v.Seq != initialSeq+10 {
		t.Errorf("expected sequence to advance by 10, got %d", v.Seq)
	}
	if v.Charging == 0 && v.OdoKM < initialOdo {
		t.Errorf("odometer should not decrease")
	}
}
