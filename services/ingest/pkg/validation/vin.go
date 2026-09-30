package validation

import (
	"errors"
	"fmt"
	"regexp"
	"time"
)

var (
	vinRegex = regexp.MustCompile(`^[A-HJ-NPR-Z0-9]{17}$`)
	dtcRegex = regexp.MustCompile(`^[PCBU][0-3][0-9A-F]{3}$`)

	vinWeights = [17]int{8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2}

	vinLetterValues = map[rune]int{
		'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8,
		'J': 1, 'K': 2, 'L': 3, 'M': 4, 'N': 5,
		'P': 7, 'R': 9,
		'S': 2, 'T': 3, 'U': 4, 'V': 5, 'W': 6, 'X': 7, 'Y': 8, 'Z': 9,
		'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
	}

	validEvents = map[string]bool{
		"NONE":        true,
		"HARSH_BRAKE": true,
		"PLUG_IN":     true,
		"PLUG_OUT":    true,
		"FAST_CHARGE": true,
		"SLOW_CHARGE": true,
		"DTC_ALERT":   true,
	}
)

var (
	ErrInvalidVINFormat    = errors.New("VIN must be 17 alphanumeric characters excluding I, O, Q")
	ErrInvalidVINChecksum  = errors.New("VIN check digit mismatch at position 9")
	ErrFutureTimestamp     = errors.New("timestamp is >5 minutes in the future")
	ErrInvalidSOC          = errors.New("SoC percentage out of range [0, 100]")
	ErrInvalidSpeed        = errors.New("speed out of range [0, 250] km/h")
	ErrInvalidBatteryTemp  = errors.New("battery temperature out of range [-40, 100] C")
	ErrInvalidCoordinates  = errors.New("latitude [-90, 90] or longitude [-180, 180] out of range")
	ErrInvalidDTC          = errors.New("DTC format invalid (must match ^[PCBU][0-3][0-9A-F]{3}$)")
	ErrInvalidEvent        = errors.New("unknown event type")
)

// ValidateVIN validates 17-char format and check-digit at position 9 (index 8).
func ValidateVIN(vin string) error {
	if len(vin) != 17 || !vinRegex.MatchString(vin) {
		return ErrInvalidVINFormat
	}

	sum := 0
	for i, ch := range vin {
		val, ok := vinLetterValues[ch]
		if !ok {
			return ErrInvalidVINFormat
		}
		sum += val * vinWeights[i]
	}

	rem := sum % 11
	var expectedCheck byte
	if rem == 10 {
		expectedCheck = 'X'
	} else {
		expectedCheck = '0' + byte(rem)
	}

	if vin[8] != expectedCheck {
		return fmt.Errorf("%w: expected %c, got %c", ErrInvalidVINChecksum, expectedCheck, vin[8])
	}

	return nil
}

// ComputeVINCheckDigit calculates the check digit character for a 17-char VIN template (where pos 9 can be placeholder).
func ComputeVINCheckDigit(vin string) (byte, error) {
	if len(vin) != 17 {
		return 0, ErrInvalidVINFormat
	}
	sum := 0
	for i := 0; i < 17; i++ {
		ch := rune(vin[i])
		if i == 8 {
			continue // weight is 0
		}
		val, ok := vinLetterValues[ch]
		if !ok {
			return 0, ErrInvalidVINFormat
		}
		sum += val * vinWeights[i]
	}
	rem := sum % 11
	if rem == 10 {
		return 'X', nil
	}
	return '0' + byte(rem), nil
}

// ValidateRanges checks physical and logical ranges for canonical telemetry.
func ValidateRanges(soc float64, speed float64, temp float64, lat float64, lon float64, ts time.Time) error {
	if soc < 0.0 || soc > 100.0 {
		return ErrInvalidSOC
	}
	if speed < 0.0 || speed > 250.0 {
		return ErrInvalidSpeed
	}
	if temp < -40.0 || temp > 100.0 {
		return ErrInvalidBatteryTemp
	}
	if lat < -90.0 || lat > 90.0 || lon < -180.0 || lon > 180.0 {
		return ErrInvalidCoordinates
	}
	// ts not > 5 min in the future
	if ts.After(time.Now().UTC().Add(5 * time.Minute)) {
		return ErrFutureTimestamp
	}
	return nil
}

// ValidateDTCs checks if each DTC matches the standard automotive diagnostic regex.
func ValidateDTCs(dtcs []string) error {
	for _, dtc := range dtcs {
		if dtc == "" {
			continue
		}
		if !dtcRegex.MatchString(dtc) {
			return fmt.Errorf("%w: %s", ErrInvalidDTC, dtc)
		}
	}
	return nil
}

// ValidateEvent checks if the event name is allowed.
func ValidateEvent(evt string) error {
	if evt == "" {
		return nil
	}
	if !validEvents[evt] {
		return fmt.Errorf("%w: %s", ErrInvalidEvent, evt)
	}
	return nil
}
