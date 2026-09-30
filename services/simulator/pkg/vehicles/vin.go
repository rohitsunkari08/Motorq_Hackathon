package vehicles

import (
	"fmt"
)

var (
	vinWeights = [17]int{8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2}

	vinLetterValues = map[byte]int{
		'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
		'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5,
		'P': 7, 'R': 9,
		'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
		'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
	}

	oemPrefixes = map[string]string{
		"VoltX":      "1VXEV",
		"NordMotors": "1NMEV",
		"AsiaDrive":  "1ADEV",
		"EuroEV":     "1EEEV",
		"ZephyrEV":   "1ZZEV",
	}
)

// GenerateVIN produces a 17-char valid VIN with a mathematically correct check digit at position 9.
func GenerateVIN(oem string, vehicleIndex int) string {
	prefix, ok := oemPrefixes[oem]
	if !ok {
		prefix = "1VXEV"
	}

	// 5-char prefix + 3-char attributes + 1 placeholder for check digit + 8-char sequential number = 17 chars
	// e.g. "1VXEV" + "01A" + "0" + "00000001"
	body := fmt.Sprintf("%s01A0%08d", prefix, vehicleIndex%100000000)
	bytes := []byte(body)

	sum := 0
	for i := 0; i < 17; i++ {
		if i == 8 {
			continue // check digit weight is 0
		}
		val := vinLetterValues[bytes[i]]
		sum += val * vinWeights[i]
	}

	rem := sum % 11
	var chk byte
	if rem == 10 {
		chk = 'X'
	} else {
		chk = '0' + byte(rem)
	}

	bytes[8] = chk
	return string(bytes)
}

// GenerateCorruptedVIN produces an invalid VIN by flipping the check digit.
func GenerateCorruptedVIN(oem string, vehicleIndex int) string {
	validVIN := GenerateVIN(oem, vehicleIndex)
	b := []byte(validVIN)
	if b[8] == '0' {
		b[8] = '1'
	} else {
		b[8] = '0'
	}
	return string(b)
}
