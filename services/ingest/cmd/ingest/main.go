package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/alerts"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/normalizer"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/sink"
)

func getEnvOrDefault(key, fallback string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return fallback
}

func main() {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	mode := flag.String("mode", getEnvOrDefault("INGEST_MODE", "normalize"), "Service mode: normalize, sink, alerts")
	brokersFlag := flag.String("brokers", "", "Kafka/Redpanda broker addresses (comma-separated)")
	
	defaultPort := 2112
	if envPort := os.Getenv("METRICS_PORT"); envPort != "" {
		if p, err := strconv.Atoi(envPort); err == nil {
			defaultPort = p
		}
	}
	metricsPort := flag.Int("metrics-port", defaultPort, "Prometheus metrics HTTP port")
	rawTopic := flag.String("raw-topic", getEnvOrDefault("RAW_TOPIC", "telemetry.raw"), "Topic for raw OEM telemetry")
	canonicalTopic := flag.String("canonical-topic", getEnvOrDefault("CANONICAL_TOPIC", "telemetry.canonical"), "Topic for normalized canonical telemetry")
	alertsTopic := flag.String("alerts-topic", getEnvOrDefault("ALERTS_TOPIC", "alerts"), "Topic for emitted alerts")
	dlqTopic := flag.String("dlq-topic", getEnvOrDefault("DLQ_TOPIC", "telemetry.dlq"), "Topic for invalid/dead-letter payloads")
	batchSize := flag.Int("batch-size", 10000, "Batch size for message fetching/sinking")
	flushInterval := flag.Duration("flush-interval", 1*time.Second, "Flush interval for sink mode")
	workers := flag.Int("workers", 16, "Number of worker goroutines")

	// ClickHouse configs
	chAddr := flag.String("clickhouse-addr", getEnvOrDefault("CLICKHOUSE_ADDR", "localhost:9000"), "ClickHouse native address (host:port)")
	chDB := flag.String("clickhouse-db", getEnvOrDefault("CLICKHOUSE_DB", "evc"), "ClickHouse database name")
	chUser := flag.String("clickhouse-user", getEnvOrDefault("CLICKHOUSE_USER", "evc"), "ClickHouse user name")
	chPassword := flag.String("clickhouse-password", getEnvOrDefault("CH_PASSWORD", getEnvOrDefault("CLICKHOUSE_PASSWORD", "change_me")), "ClickHouse password")

	// Redis configs
	redisAddr := flag.String("redis-addr", getEnvOrDefault("REDIS_ADDR", "localhost:6379"), "Redis address (host:port)")
	redisPassword := flag.String("redis-password", getEnvOrDefault("REDIS_PASSWORD", ""), "Redis password")

	// Postgres configs
	pgDefaultURL := "postgres://evc:change_me@localhost:5432/evc?sslmode=disable"
	if envPG := os.Getenv("POSTGRES_URL"); envPG != "" {
		pgDefaultURL = envPG
	} else if envDB := os.Getenv("DATABASE_URL"); envDB != "" {
		pgDefaultURL = envDB
	}
	pgURL := flag.String("postgres-url", pgDefaultURL, "Postgres connection URL")

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
		log.Info().Str("addr", addr).Str("mode", *mode).Msg("Starting metrics server")
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
		cfg := sink.Config{
			Brokers:            brokerList,
			CanonicalTopic:     *canonicalTopic,
			ConsumerGroup:      "ingest-sink-group",
			BatchSize:          *batchSize,
			FlushInterval:      *flushInterval,
			ClickHouseAddr:     *chAddr,
			ClickHouseDB:       *chDB,
			ClickHouseUser:     *chUser,
			ClickHousePassword: *chPassword,
			RedisAddr:          *redisAddr,
			RedisPassword:      *redisPassword,
		}
		svc, err := sink.NewService(cfg)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed initializing sink service")
		}
		if err := svc.Start(ctx); err != nil {
			log.Fatal().Err(err).Msg("Sink service error")
		}

	case "alerts":
		cfg := alerts.Config{
			Brokers:        brokerList,
			CanonicalTopic: *canonicalTopic,
			AlertsTopic:    *alertsTopic,
			ConsumerGroup:  "ingest-alerts-group",
			PostgresURL:    *pgURL,
			RedisAddr:      *redisAddr,
			RedisPassword:  *redisPassword,
			NumWorkers:     *workers,
			BatchSize:      *batchSize,
		}
		svc, err := alerts.NewService(cfg)
		if err != nil {
			log.Fatal().Err(err).Msg("Failed initializing alerts service")
		}
		if err := svc.Start(ctx); err != nil {
			log.Fatal().Err(err).Msg("Alerts service error")
		}

	default:
		log.Fatal().Str("mode", *mode).Msg("Invalid mode specified (must be normalize, sink, alerts)")
	}

	log.Info().Str("mode", *mode).Msg("Ingest service stopped cleanly")
}
