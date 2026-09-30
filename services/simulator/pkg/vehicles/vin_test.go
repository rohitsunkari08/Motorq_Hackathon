package vehicles_test

import (
	"regexp"
	"testing"

	"github.com/rohitsunkari08/evc/services/simulator/pkg/vehicles"
)

var vinWeights = [17]int{8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2}
var vinLetterValues = map[byte]int{
	'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
	'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5,
	'P': 7, 'R': 9,
	'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
	'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
}

func validateVINString(vin string) bool {
	if len(vin) != 17 || !regexp.MustCompile(`^[A-HJ-NPR-Z0-9]{17}$`).MatchString(vin) {
		return false
	}
	sum := 0
	for i := 0; i < 17; i++ {
		val, ok := vinLetterValues[vin[i]]
		if !ok {
			return false
		}
		sum += val * vinWeights[i]
	}
	rem := sum % 11
	var expected byte
	if rem == 10 {
		expected = 'X'
	} else {
		expected = '0' + byte(rem)
	}
	return vin[8] == expected
}

func TestGenerateVIN(t *testing.T) {
	oems := []string{"VoltX", "NordMotors", "AsiaDrive", "EuroEV", "ZephyrEV"}

	for _, oem := range oems {
		for i := 1; i <= 200; i++ {
			vin := vehicles.GenerateVIN(oem, i)
			if !validateVINString(vin) {
				t.Fatalf("OEM %s generated invalid VIN: %s", oem, vin)
			}
		}
	}
}

func TestGenerateCorruptedVIN(t *testing.T) {
	for i := 1; i <= 50; i++ {
		corrupted := vehicles.GenerateCorruptedVIN("VoltX", i)
		if validateVINString(corrupted) {
			t.Fatalf("Corrupted VIN unexpectedly validated as true: %s", corrupted)
		}
	}
}
