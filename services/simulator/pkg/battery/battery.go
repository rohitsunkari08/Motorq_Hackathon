package battery

import (
	"math"
)

// Model coefficients calibrated to published aggregates (Geotab 2026, references.md R1):
// Fleet mean degradation ~2.3%/yr, low-DC-fast vehicles ~1.5%/yr, heavy >100kW DC users ~3.0%/yr.
// Baseline 1 year: ~45 Equivalent Full Cycles (EFC) (~15,000 km / 60 kWh pack).
const (
	coeffCycle   = 0.00160 // a * sqrt(EFC) (~1.07% base cycling)
	coeffDCFast  = 0.00040 // b * dc_fast_share * EFC (~0.27% to 1.17%)
	coeffThermal = 0.00025 // c * hot_exposure (~0.25% to 0.75%)
)

// ComputeSoH calculates the true State of Health (0.0 to 1.0) using the physical battery model:
// SoH = 1 - a*sqrt(EFC) - b*dc_fast_share*EFC - c*hot_exposure + noise
func ComputeSoH(efc float64, dcFastShare float64, hotExposure float64, noise float64) float64 {
	if efc < 0 {
		efc = 0
	}
	if dcFastShare < 0 {
		dcFastShare = 0
	} else if dcFastShare > 1.0 {
		dcFastShare = 1.0
	}

	degradation := coeffCycle*math.Sqrt(efc) + coeffDCFast*dcFastShare*efc + coeffThermal*hotExposure - noise
	soh := 1.0 - degradation

	// Physical limits: SoH typically between 0.65 (end of life) and 1.0 (fresh)
	if soh > 1.0 {
		soh = 1.0
	} else if soh < 0.65 {
		soh = 0.65
	}

	return math.Round(soh*10000) / 10000
}
