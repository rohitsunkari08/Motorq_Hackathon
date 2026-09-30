package dedupe

import (
	"fmt"
	"sync"

	"github.com/bits-and-blooms/bloom/v3"
)

type PartitionBloomDeduper struct {
	mu          sync.Mutex
	capacity    uint
	fpRate      float64
	filters     map[int32]*bloom.BloomFilter
	filterLocks map[int32]*sync.Mutex
}

func NewPartitionBloomDeduper(capacity uint, fpRate float64) *PartitionBloomDeduper {
	if capacity == 0 {
		capacity = 10_000_000
	}
	if fpRate <= 0 || fpRate >= 1 {
		fpRate = 0.001 // 0.1% FP
	}
	return &PartitionBloomDeduper{
		capacity:    capacity,
		fpRate:      fpRate,
		filters:     make(map[int32]*bloom.BloomFilter),
		filterLocks: make(map[int32]*sync.Mutex),
	}
}

func (d *PartitionBloomDeduper) getFilter(partition int32) (*bloom.BloomFilter, *sync.Mutex) {
	d.mu.Lock()
	defer d.mu.Unlock()

	f, ok := d.filters[partition]
	if !ok {
		f = bloom.NewWithEstimates(d.capacity, d.fpRate)
		d.filters[partition] = f
		d.filterLocks[partition] = &sync.Mutex{}
	}
	return f, d.filterLocks[partition]
}

// IsDuplicate returns true if (vin, seq) has already been seen in this partition.
func (d *PartitionBloomDeduper) IsDuplicate(partition int32, vin string, seq uint64) bool {
	f, l := d.getFilter(partition)
	l.Lock()
	defer l.Unlock()

	key := []byte(fmt.Sprintf("%s:%d", vin, seq))
	return f.TestAndAdd(key)
}

// Reset clears the filter for a partition (e.g. periodically or on rebalance)
func (d *PartitionBloomDeduper) Reset(partition int32) {
	d.mu.Lock()
	defer d.mu.Unlock()
	d.filters[partition] = bloom.NewWithEstimates(d.capacity, d.fpRate)
}
