package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/normalizer"
)

func main() {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	mode := flag.String("mode", "normalize", "Service mode: normalize, sink, alerts")
	brokersFlag := flag.String("brokers", "", "Kafka/Redpanda broker addresses (comma-separated)")
	metricsPort := flag.Int("metrics-port", 2112, "Prometheus metrics HTTP port")
	rawTopic := flag.String("raw-topic", "telemetry.raw", "Topic for raw OEM telemetry")
	canonicalTopic := flag.String("canonical-topic", "telemetry.canonical", "Topic for normalized canonical telemetry")
	dlqTopic := flag.String("dlq-topic", "telemetry.dlq", "Topic for invalid/dead-letter payloads")
	batchSize := flag.Int("batch-size", 10000, "Batch size for message fetching")
	workers := flag.Int("workers", 16, "Number of worker goroutines")
	flag.Parse()

	// Broker address discovery
	brokerList := []string{}
	if *brokersFlag != "" {
		brokerList = strings.Split(*brokersFlag, ",")
	} else if envBrokers := os.Getenv("KAFKA_BROKERS"); envBrokers != "" {
		brokerList = strings.Split(envBrokers, ",")
	} else {
		brokerList = []string{"localhost:19092"}
	}

	for i := range brokerList {
		brokerList[i] = strings.TrimSpace(brokerList[i])
	}

	// Start Prometheus metrics server
	http.Handle("/metrics", promhttp.Handler())
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})
	go func() {
		addr := fmt.Sprintf(":%d", *metricsPort)
		log.Info().Str("addr", addr).Msg("Starting metrics server")
		if err := http.ListenAndServe(addr, nil); err != nil && err != http.ErrServerClosed {
			log.Error().Err(err).Msg("Metrics server failure")
		}
	}()

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	switch *mode {
	case "normalize":
		cfg := normalizer.Config{
			Brokers:        brokerList,
			RawTopic:       *rawTopic,
			CanonicalTopic: *canonicalTopic,
			DLQTopic:       *dlqTopic,
			ConsumerGroup:  "ingest-normalize-group",
			BatchSize:      *batchSize,
			NumWorkers:     *workers,
		}
		svc, err := normalizer.NewService(cfg)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed initializing normalizer service")
		}
		if err := svc.Start(ctx); err != nil {
			log.Fatal().Err(err).Msg("Normalizer service error")
		}

	case "sink":
		log.Info().Msg("Sink mode placeholder (scheduled for P2)")
		<-ctx.Done()

	case "alerts":
		log.Info().Msg("Alerts mode placeholder (scheduled for P2)")
		<-ctx.Done()

	default:
		log.Fatal().Str("mode", *mode).Msg("Invalid mode specified (must be normalize, sink, alerts)")
	}

	log.Info().Msg("Ingest service stopped cleanly")
}
