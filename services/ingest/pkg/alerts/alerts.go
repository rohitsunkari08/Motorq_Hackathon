package alerts

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
	"github.com/twmb/franz-go/pkg/kgo"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/metrics"
)

type Config struct {
	Brokers        []string
	CanonicalTopic string
	AlertsTopic    string
	ConsumerGroup  string
	PostgresURL    string
	RedisAddr      string
	RedisPassword  string
	NumWorkers     int
	BatchSize      int
}

type Service struct {
	cfg       Config
	client    *kgo.Client
	chargers  *ChargerIndex
	params    *VehicleParamsStore
	windows   *WindowManager
	engine    *RuleEngine
	debouncer *Debouncer
	rdb       *redis.Client
	stopOnce  sync.Once
	stopChan  chan struct{}
}

func NewService(cfg Config) (*Service, error) {
	if cfg.CanonicalTopic == "" {
		cfg.CanonicalTopic = "telemetry.canonical"
	}
	if cfg.AlertsTopic == "" {
		cfg.AlertsTopic = "alerts"
	}
	if cfg.ConsumerGroup == "" {
		cfg.ConsumerGroup = "ingest-alerts-group"
	}
	if cfg.NumWorkers <= 0 {
		cfg.NumWorkers = 8
	}
	if cfg.BatchSize <= 0 {
		cfg.BatchSize = 5000
	}

	var rdb *redis.Client
	if cfg.RedisAddr != "" {
		rdb = redis.NewClient(&redis.Options{
			Addr:     cfg.RedisAddr,
			Password: cfg.RedisPassword,
			DB:       0,
		})
	}

	chargers := NewChargerIndex()
	params := NewVehicleParamsStore(rdb)
	windows := NewWindowManager()
	engine := NewRuleEngine(chargers, params, windows)
	debouncer := NewDebouncer(10 * time.Minute)

	// Kafka client for consuming canonical telemetry and producing alerts
	opts := []kgo.Opt{
		kgo.SeedBrokers(cfg.Brokers...),
		kgo.ConsumerGroup(cfg.ConsumerGroup),
		kgo.ConsumeTopics(cfg.CanonicalTopic),
		kgo.ConsumeResetOffset(kgo.NewOffset().AtStart()),
		kgo.FetchMaxBytes(20 * 1024 * 1024),
		kgo.RequiredAcks(kgo.AllISRAcks()),
		kgo.ProducerBatchMaxBytes(1024 * 1024),
		kgo.ProducerLinger(5 * time.Millisecond),
	}

	client, err := kgo.NewClient(opts...)
	if err != nil {
		return nil, fmt.Errorf("failed creating Kafka client for alerts: %w", err)
	}

	return &Service{
		cfg:       cfg,
		client:    client,
		chargers:  chargers,
		params:    params,
		windows:   windows,
		engine:    engine,
		debouncer: debouncer,
		rdb:       rdb,
		stopChan:  make(chan struct{}),
	}, nil
}

func (s *Service) Start(ctx context.Context) error {
	log.Info().
		Str("canonical_topic", s.cfg.CanonicalTopic).
		Str("alerts_topic", s.cfg.AlertsTopic).
		Str("consumer_group", s.cfg.ConsumerGroup).
		Msg("Starting ingest alerts service")

	// Hydrate charger index and vehicle params from Postgres if available
	loadCtx, loadCancel := context.WithTimeout(ctx, 10*time.Second)
	_ = s.chargers.LoadFromPostgres(loadCtx, s.cfg.PostgresURL)
	_ = s.params.LoadFromPostgres(loadCtx, s.cfg.PostgresURL)
	loadCancel()

	// Launch debouncer periodic cleaner
	go func() {
		ticker := time.NewTicker(15 * time.Minute)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-s.stopChan:
				return
			case now := <-ticker.C:
				s.debouncer.CleanStale(now)
			}
		}
	}()

	recordChan := make(chan *kgo.Record, s.cfg.BatchSize*2)
	var wg sync.WaitGroup

	for i := 0; i < s.cfg.NumWorkers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for rec := range recordChan {
				s.processRecord(ctx, rec)
			}
		}()
	}

	defer func() {
		close(recordChan)
		wg.Wait()
		s.client.Close()
		if s.rdb != nil {
			s.rdb.Close()
		}
	}()

	for {
		select {
		case <-ctx.Done():
			return nil
		case <-s.stopChan:
			return nil
		default:
		}

		fetches := s.client.PollFetches(ctx)
		if fetches.IsClientClosed() {
			return nil
		}
		if errs := fetches.Errors(); len(errs) > 0 {
			for _, err := range errs {
				log.Warn().Err(err.Err).Str("topic", err.Topic).Int32("partition", err.Partition).Msg("Alerts fetch error")
			}
		}

		iter := fetches.RecordIter()
		for !iter.Done() {
			rec := iter.Next()
			select {
			case recordChan <- rec:
			case <-ctx.Done():
				return nil
			case <-s.stopChan:
				return nil
			}
		}

		if err := s.client.CommitUncommittedOffsets(ctx); err != nil {
			log.Warn().Err(err).Msg("Alerts consumer offset commit error")
		}
	}
}

func (s *Service) Stop() {
	s.stopOnce.Do(func() {
		close(s.stopChan)
	})
}

func (s *Service) processRecord(ctx context.Context, rec *kgo.Record) {
	var ev canonical.Event
	if err := json.Unmarshal(rec.Value, &ev); err != nil {
		log.Warn().Err(err).Msg("Failed unmarshaling canonical record in alerts worker")
		return
	}

	// Evaluate rules
	alerts := s.engine.EvaluateRules(ctx, &ev)
	if len(alerts) == 0 {
		return
	}

	now := time.Now().UTC()
	for _, alert := range alerts {
		// Check debouncing per (vin, type) 10 min
		if !s.debouncer.ShouldEmit(alert.VIN, alert.Type, now) {
			continue
		}

		// Calculate latency from canonical event timestamp to alert emission
		latencySec := now.Sub(ev.TS.UTC()).Seconds()
		if latencySec < 0 {
			latencySec = 0
		}
		alert.EmitTS = now.Format(time.RFC3339Nano)
		alert.LatencyMS = latencySec * 1000.0

		// Update metrics
		metrics.AlertLatency.Observe(latencySec)
		metrics.AlertsEmittedTotal.WithLabelValues(alert.Type, alert.Severity).Inc()

		payload, err := json.Marshal(alert)
		if err != nil {
			log.Error().Err(err).Msg("Failed marshaling alert event")
			continue
		}

		outRecord := &kgo.Record{
			Topic: s.cfg.AlertsTopic,
			Key:   []byte(alert.VIN),
			Value: payload,
		}

		s.client.Produce(ctx, outRecord, func(r *kgo.Record, err error) {
			if err != nil {
				log.Error().Err(err).Str("vin", alert.VIN).Str("type", alert.Type).Msg("Failed producing alert to topic")
			} else {
				log.Info().
					Str("vin", alert.VIN).
					Str("type", alert.Type).
					Str("severity", alert.Severity).
					Float64("latency_ms", alert.LatencyMS).
					Msg("Alert emitted")
			}
		})
	}
}

// GetRuleEngine exposes the rule engine for unit testing
func (s *Service) GetRuleEngine() *RuleEngine {
	return s.engine
}

// GetDebouncer exposes the debouncer for unit testing
func (s *Service) GetDebouncer() *Debouncer {
	return s.debouncer
}
