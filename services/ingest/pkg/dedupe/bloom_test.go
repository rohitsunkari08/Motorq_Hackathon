package dedupe_test

import (
	"fmt"
	"testing"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/dedupe"
)

func TestPartitionBloomDeduper(t *testing.T) {
	d := dedupe.NewPartitionBloomDeduper(100_000, 0.001)

	vin1 := "1HGCR2F83HA000001"
	vin2 := "1HGCR2F83HA000002"

	// First time seen in partition 0 -> not duplicate
	if d.IsDuplicate(0, vin1, 1) {
		t.Errorf("expected first occurrence to not be duplicate")
	}

	// Second time seen in partition 0 -> DUPLICATE
	if !d.IsDuplicate(0, vin1, 1) {
		t.Errorf("expected second occurrence to be duplicate")
	}

	// Different seq -> not duplicate
	if d.IsDuplicate(0, vin1, 2) {
		t.Errorf("expected new seq 2 to not be duplicate")
	}

	// Different vin -> not duplicate
	if d.IsDuplicate(0, vin2, 1) {
		t.Errorf("expected new vin to not be duplicate")
	}

	// Different partition with same vin/seq -> not duplicate
	if d.IsDuplicate(1, vin1, 1) {
		t.Errorf("expected different partition to not be duplicate")
	}

	// Stress test with 10,000 unique records in partition 0
	dupes := 0
	for seq := uint64(10); seq < 10010; seq++ {
		if d.IsDuplicate(0, fmt.Sprintf("VIN%06d", seq), seq) {
			dupes++
		}
	}
	// With 0.1% FP, dupes should be < 20 out of 10,000
	if dupes > 20 {
		t.Errorf("excessive false positives: %d/10000", dupes)
	}
}
