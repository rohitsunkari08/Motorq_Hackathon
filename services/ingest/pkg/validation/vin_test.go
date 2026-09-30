package validation_test

import (
	"testing"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/validation"
)

func TestValidateVIN(t *testing.T) {
	// Valid 17-char VINs with correct check digits at index 8 (pos 9)
	validVINs := []string{
		"1HGCR2F83HA000000",
		"1FTFW1ED4MFA00001",
		"WAUZZZ8V7KA000002",
		"5YJ3E1EB8NF000003",
		"KM8K23AG6NU000004",
	}

	for _, vin := range validVINs {
		// First compute what check digit should be
		chk, err := validation.ComputeVINCheckDigit(vin)
		if err != nil {
			t.Fatalf("failed computing check digit for %s: %v", vin, err)
		}
		// Form valid VIN with that check digit
		bytes := []byte(vin)
		bytes[8] = chk
		validVinWithChk := string(bytes)

		if err := validation.ValidateVIN(validVinWithChk); err != nil {
			t.Errorf("expected valid VIN for %s, got: %v", validVinWithChk, err)
		}
	}

	// Invalid VINs
	invalidCases := []struct {
		vin string
		msg string
	}{
		{"1HGCR2F83HA00000", "too short (16 chars)"},
		{"1HGCR2F83HA0000000", "too long (18 chars)"},
		{"1HGCR2F83IA000000", "contains illegal letter 'I'"},
		{"1HGCR2F83OA000000", "contains illegal letter 'O'"},
		{"1HGCR2F83QA000000", "contains illegal letter 'Q'"},
		{"1HGCR2F80HA000000", "wrong check digit"},
	}

	for _, tc := range invalidCases {
		if err := validation.ValidateVIN(tc.vin); err == nil {
			t.Errorf("expected error for case '%s' (%s), got nil", tc.msg, tc.vin)
		}
	}
}

func TestValidateRanges(t *testing.T) {
	now := time.Now().UTC()

	// Valid case
	if err := validation.ValidateRanges(80.0, 60.0, 25.0, 37.77, -122.41, now); err != nil {
		t.Errorf("unexpected error on valid ranges: %v", err)
	}

	// Negative SoC
	if err := validation.ValidateRanges(-1.0, 60.0, 25.0, 37.77, -122.41, now); err == nil {
		t.Error("expected error on negative SoC")
	}

	// SoC > 100
	if err := validation.ValidateRanges(101.0, 60.0, 25.0, 37.77, -122.41, now); err == nil {
		t.Error("expected error on SoC > 100")
	}

	// Speed > 250
	if err := validation.ValidateRanges(50.0, 260.0, 25.0, 37.77, -122.41, now); err == nil {
		t.Error("expected error on Speed > 250")
	}

	// Negative Speed
	if err := validation.ValidateRanges(50.0, -5.0, 25.0, 37.77, -122.41, now); err == nil {
		t.Error("expected error on negative speed")
	}

	// Temp > 100
	if err := validation.ValidateRanges(50.0, 60.0, 105.0, 37.77, -122.41, now); err == nil {
		t.Error("expected error on temp > 100")
	}

	// Temp < -40
	if err := validation.ValidateRanges(50.0, 60.0, -45.0, 37.77, -122.41, now); err == nil {
		t.Error("expected error on temp < -40")
	}

	// Invalid latitude
	if err := validation.ValidateRanges(50.0, 60.0, 25.0, 95.0, -122.41, now); err == nil {
		t.Error("expected error on latitude > 90")
	}

	// Timestamp > 5 min in future
	futureTime := now.Add(10 * time.Minute)
	if err := validation.ValidateRanges(50.0, 60.0, 25.0, 37.77, -122.41, futureTime); err == nil {
		t.Error("expected error on timestamp > 5 min in future")
	}
}

func TestValidateDTCs(t *testing.T) {
	validDTCs := []string{"P0123", "C1234", "B0001", "U0100"}
	if err := validation.ValidateDTCs(validDTCs); err != nil {
		t.Errorf("unexpected error on valid DTCs: %v", err)
	}

	invalidDTCs := []string{"X1234", "P9999", "12345", "P01"}
	for _, dtc := range invalidDTCs {
		if err := validation.ValidateDTCs([]string{dtc}); err == nil {
			t.Errorf("expected error on invalid DTC: %s", dtc)
		}
	}
}
