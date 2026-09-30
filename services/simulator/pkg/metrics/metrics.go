package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

var (
	EventsSentTotal = promauto.NewCounter(
		prometheus.CounterOpts{
			Name: "events_sent_total",
			Help: "Total number of simulated telemetry events sent to Kafka",
		},
	)

	SendRate = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "send_rate",
			Help: "Current rate of simulated events sent per second",
		},
	)
)
