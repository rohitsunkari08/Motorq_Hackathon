package main

import (
	"context"
	"flag"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"sync/atomic"
	"syscall"
	"time"

	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"

	"github.com/rohitsunkari08/evc/services/simulator/pkg/generator"
	"github.com/rohitsunkari08/evc/services/simulator/pkg/metrics"
	"github.com/rohitsunkari08/evc/services/simulator/pkg/producer"
	"github.com/rohitsunkari08/evc/services/simulator/pkg/vehicles"
)

func main() {
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	mode := flag.String("mode", "live", "Simulator mode: live or seed")
	rate := flag.Int("rate", 100000, "Target events per second")
	numVehicles := flag.Int("vehicles", 100000, "Number of simulated vehicles")
	burstMultiplier := flag.Float64("burst", 1.0, "Burst rate multiplier")
	burstDuration := flag.Duration("burst-duration", 5*time.Minute, "Burst duration")
	brokersFlag := flag.String("brokers", "", "Kafka/Redpanda brokers")
	metricsPort := flag.Int("metrics-port", 2113, "Prometheus metrics port")
	runDuration := flag.Duration("duration", 0, "Run duration (0 = continuous)")
	seed := flag.Int64("seed", 42, "Deterministic random seed")
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
		log.Info().Str("addr", addr).Msg("Starting simulator metrics server")
		if err := http.ListenAndServe(addr, nil); err != nil && err != http.ErrServerClosed {
			log.Error().Err(err).Msg("Simulator metrics server failure")
		}
	}()

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	if *runDuration > 0 {
		var cancelDuration context.CancelFunc
		ctx, cancelDuration = context.WithTimeout(ctx, *runDuration)
		defer cancelDuration()
	}

	switch *mode {
	case "live":
		runLiveSimulation(ctx, brokerList, *numVehicles, *rate, *burstMultiplier, *burstDuration, *seed)
	case "seed":
		log.Info().Int("vehicles", *numVehicles).Msg("Seed mode requested (scheduled for P3 database hydration)")
	default:
		log.Fatal().Str("mode", *mode).Msg("Invalid mode: must be live or seed")
	}

	log.Info().Msg("Simulator shutdown cleanly")
}

func runLiveSimulation(ctx context.Context, brokers []string, numVehicles int, targetRate int, burstMult float64, burstDur time.Duration, seed int64) {
	log.Info().
		Int("vehicles", numVehicles).
		Int("target_rate", targetRate).
		Float64("burst", burstMult).
		Strs("brokers", brokers).
		Msg("Initializing live multi-OEM fleet simulation")

	fleet := vehicles.NewFleet(numVehicles, seed)
	formatter := generator.NewFormatter(seed)

	prod, err := producer.NewProducer(producer.Config{
		Brokers:  brokers,

		Topic:    "telemetry.raw",
		Linger:   5 * time.Millisecond,
		BatchMax: 1024 * 1024,
	})
	if err != nil {
		log.Fatal().Err(err).Msg("Failed creating Kafka producer")
	}
	defer prod.Close()

	startTime := time.Now()
	var sentCount uint64
	var lastReportedCount uint64
	lastReportTime := time.Now()

	// Rate monitoring goroutine
	go func() {
		ticker := time.NewTicker(1 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case now := <-ticker.C:
				current := atomic.LoadUint64(&sentCount)
				delta := current - lastReportedCount
				dt := now.Sub(lastReportTime).Seconds()
				rateSec := float64(delta) / dt
				metrics.SendRate.Set(rateSec)
				log.Info().Float64("rate_ev_s", rateSec).Uint64("total_sent", current).Msg("Telemetry throughput")
				lastReportedCount = current
				lastReportTime = now
			}
		}
	}()

	currentVehicleIdx := 0
	burstEndTime := startTime.Add(burstDur)

	// Work in batches for maximum efficiency and exact rate regulation
	batchSize := 2000
	if targetRate < batchSize {
		batchSize = targetRate
	}

	for {
		select {
		case <-ctx.Done():
			totalElapsed := time.Since(startTime).Seconds()
			finalSent := atomic.LoadUint64(&sentCount)
			if totalElapsed > 0 {
				overallRate := float64(finalSent) / totalElapsed
				metrics.SendRate.Set(overallRate)
				log.Info().Float64("rate_ev_s", overallRate).Uint64("total_sent", finalSent).Msg("Overall simulation throughput")
			}
			log.Info().Msg("Context cancelled, draining producer...")
			prod.Flush(context.Background())
			return
		default:
		}

		// Calculate current desired rate
		curRate := float64(targetRate)
		if burstMult > 1.0 && time.Now().Before(burstEndTime) {
			curRate *= burstMult
		}

		batchStart := time.Now()
		batchExpectedDuration := time.Duration(float64(batchSize) / curRate * float64(time.Second))

		for b := 0; b < batchSize; b++ {
			if ctx.Err() != nil {
				break
			}
			v := fleet.GetVehicle(currentVehicleIdx)
			currentVehicleIdx = (currentVehicleIdx + 1) % numVehicles

			// Advance vehicle state slightly
			fleet.Step(v, 1.0)

			// Format into OEM raw payload with realistic noise
			item := formatter.FormatEvent(v, time.Now().UTC(), true)

			prod.Send(ctx, item, func(err error) {
				if err != nil {
					log.Warn().Err(err).Msg("Send error")
				}
			})

			atomic.AddUint64(&sentCount, 1)

			// Occasional duplicate (~1-2%) per §5.3
			if b%75 == 0 {
				prod.Send(ctx, item, nil)
				atomic.AddUint64(&sentCount, 1)
			}
		}

		elapsed := time.Since(batchStart)
		if elapsed < batchExpectedDuration {
			time.Sleep(batchExpectedDuration - elapsed)
		}
	}
}
