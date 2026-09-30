package generator_test

import (
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/rohitsunkari08/evc/services/simulator/pkg/generator"
	"github.com/rohitsunkari08/evc/services/simulator/pkg/vehicles"
)

func TestFormatterAllOEMs(t *testing.T) {
	fleet := vehicles.NewFleet(5, 42)
	formatter := generator.NewFormatter(42)
	now := time.Now().UTC()

	oemsTested := make(map[string]bool)

	for i := 0; i < 5; i++ {
		v := fleet.GetVehicle(i)
		res := formatter.FormatEvent(v, now, false)

		if res.OEM != v.OEM {
			t.Errorf("OEM mismatch: expected %s, got %s", v.OEM, res.OEM)
		}
		if res.VIN != v.VIN {
			t.Errorf("VIN mismatch: expected %s, got %s", v.VIN, res.VIN)
		}
		if len(res.Payload) == 0 {
			t.Fatalf("empty payload for %s", v.OEM)
		}

		oemsTested[res.OEM] = true

		switch res.OEM {
		case "VoltX", "NordMotors", "EuroEV", "ZephyrEV":
			var m map[string]interface{}
			if err := json.Unmarshal(res.Payload, &m); err != nil {
				t.Errorf("%s payload is not valid JSON: %v", res.OEM, err)
			}
		case "AsiaDrive":
			if !strings.Contains(string(res.Payload), "|") {
				t.Errorf("AsiaDrive payload missing pipe delimiter: %s", string(res.Payload))
			}
		}
	}

	for _, oem := range vehicles.OEMList {
		if !oemsTested[oem] {
			t.Errorf("OEM %s was not tested", oem)
		}
	}
}
