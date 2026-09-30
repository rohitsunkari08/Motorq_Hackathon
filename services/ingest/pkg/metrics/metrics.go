package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	IngestEventsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "ingest_events_total",
			Help: "Total number of ingested OEM telemetry events by OEM",
		},
		[]string{"oem"},
	)

	InvalidTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "invalid_total",
			Help: "Total number of invalid events sent to DLQ by rejection reason",
		},
		[]string{"reason"},
	)

	DedupeDroppedTotal = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "dedupe_dropped_total",
			Help: "Total number of duplicate events dropped by Bloom filter",
		},
	)

	NormalizeLatency = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "normalize_latency_seconds",
			Help:    "Latency of normalisation pipeline from raw payload to canonical event",
			Buckets: []float64{0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1},
		},
	)

	SinkBatchSeconds = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "sink_batch_seconds",
			Help:    "Time taken to flush a batch of events to ClickHouse",
			Buckets: []float64{0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0},
		},
	)

	RowsInsertedTotal = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "rows_inserted_total",
			Help: "Total number of canonical telemetry rows inserted into storage",
		},
	)

	AlertLatency = promauto.NewHistogram(
		prometheus.HistogramOpts{
			Name:    "alert_latency_seconds",
			Help:    "Latency from canonical event occurrence to alert emission",
			Buckets: []float64{0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0},
		},
	)

	AlertsEmittedTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "alerts_emitted_total",
			Help: "Total number of alerts emitted by type and severity",
		},
		[]string{"type", "severity"},
	)

	SinkErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "sink_errors_total",
			Help: "Total number of errors encountered during sink operations by target",
		},
		[]string{"target"},
	)
)
