package adapters

import (
	"bytes"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
)

type AsiaDriveAdapter struct{}

func (a *AsiaDriveAdapter) OEM() string {
	return "AsiaDrive"
}

func (a *AsiaDriveAdapter) CanParse(raw []byte) bool {
	trimmed := bytes.TrimSpace(raw)
	// AsiaDrive is pipe-delimited, not JSON (does not start with '{')
	if len(trimmed) > 0 && trimmed[0] != '{' && bytes.Contains(trimmed, []byte("|")) {
		return true
	}
	return false
}

func (a *AsiaDriveAdapter) Parse(raw []byte) (*canonical.Event, error) {
	str := strings.TrimSpace(string(raw))
	if str == "" {
		return nil, errors.New("asiadrive empty payload")
	}

	parts := strings.Split(str, "|")
	if len(parts) < 9 {
		return nil, fmt.Errorf("asiadrive expected at least 9 pipe-delimited fields, got %d", len(parts))
	}

	vin := strings.TrimSpace(parts[0])
	epochMs, err := strconv.ParseInt(strings.TrimSpace(parts[1]), 10, 64)
	if err != nil {
		return nil, fmt.Errorf("asiadrive invalid epoch_ms: %w", err)
	}

	lat, err := strconv.ParseFloat(strings.TrimSpace(parts[2]), 64)
	if err != nil {
		return nil, fmt.Errorf("asiadrive invalid lat: %w", err)
	}

	lon, err := strconv.ParseFloat(strings.TrimSpace(parts[3]), 64)
	if err != nil {
		return nil, fmt.Errorf("asiadrive invalid lon: %w", err)
	}

	kmh, err := strconv.ParseFloat(strings.TrimSpace(parts[4]), 64)
	if err != nil {
		return nil, fmt.Errorf("asiadrive invalid kmh: %w", err)
	}

	soc, err := strconv.ParseFloat(strings.TrimSpace(parts[5]), 64)
	if err != nil {
		return nil, fmt.Errorf("asiadrive invalid soc: %w", err)
	}

	odo, err := strconv.ParseFloat(strings.TrimSpace(parts[6]), 64)
	if err != nil {
		return nil, fmt.Errorf("asiadrive invalid odo: %w", err)
	}

	tempC, err := strconv.ParseFloat(strings.TrimSpace(parts[7]), 64)
	if err != nil {
		return nil, fmt.Errorf("asiadrive invalid tempC: %w", err)
	}

	chgKW, err := strconv.ParseFloat(strings.TrimSpace(parts[8]), 64)
	if err != nil {
		return nil, fmt.Errorf("asiadrive invalid chg_kw: %w", err)
	}

	var dtcs []string
	var seq uint64 = 0
	evt := "NONE"

	if len(parts) >= 10 {
		remainder := parts[9]
		// Remainder format could be "DTC1,DTC2;" or "DTC1,DTC2;seq;evt"
		subparts := strings.Split(remainder, ";")
		dtcPart := strings.TrimSpace(subparts[0])
		if dtcPart != "" {
			for _, d := range strings.Split(dtcPart, ",") {
				d = strings.TrimSpace(d)
				if d != "" {
					dtcs = append(dtcs, d)
				}
			}
		}
		if len(subparts) > 1 && subparts[1] != "" {
			if s, err := strconv.ParseUint(strings.TrimSpace(subparts[1]), 10, 64); err == nil {
				seq = s
			}
		}
		if len(subparts) > 2 && subparts[2] != "" {
			evt = strings.TrimSpace(subparts[2])
		}
	}

	if dtcs == nil {
		dtcs = []string{}
	}

	charging := 0
	if chgKW > 0.05 {
		charging = 1
	}

	t := time.UnixMilli(epochMs).UTC()

	event := &canonical.Event{
		SchemaV:   1,
		VIN:       vin,
		TS:        t,
		Seq:       seq,
		OEM:       a.OEM(),
		Lat:       lat,
		Lon:       lon,
		SpeedKMH:  kmh,
		SOCPct:    soc,
		OdoKM:     odo,
		BattTempC: tempC,
		Charging:  charging,
		ChargeKW:  chgKW,
		DTC:       dtcs,
		Evt:       evt,
	}
	event.PopulateGeohash()

	return event, nil
}
