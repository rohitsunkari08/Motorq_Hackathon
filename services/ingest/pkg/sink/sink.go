package sink

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/ClickHouse/clickhouse-go/v2/lib/driver"
	"github.com/redis/go-redis/v9"
	"github.com/rs/zerolog/log"
	"github.com/twmb/franz-go/pkg/kgo"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/canonical"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/metrics"
)

type Config struct {
	Brokers            []string
	CanonicalTopic     string
	ConsumerGroup      string
	BatchSize          int
	FlushInterval      time.Duration
	ClickHouseAddr     string
	ClickHouseDB       string
	ClickHouseUser     string
	ClickHousePassword string
	RedisAddr          string
	RedisPassword      string
}

type Service struct {
	cfg        Config
	client     *kgo.Client
	chConn     driver.Conn
	rdb        *redis.Client
	stopOnce   sync.Once
	stopChan   chan struct{}
	mu         sync.Mutex
	eventBuf   []*canonical.Event
	latestByVIN map[string]*canonical.Event
	lastFlush  time.Time
}

func NewService(cfg Config) (*Service, error) {
	if cfg.CanonicalTopic == "" {
		cfg.CanonicalTopic = "telemetry.canonical"
	}
	if cfg.ConsumerGroup == "" {
		cfg.ConsumerGroup = "ingest-sink-group"
	}
	if cfg.BatchSize <= 0 {
		cfg.BatchSize = 100000
	}
	if cfg.FlushInterval <= 0 {
		cfg.FlushInterval = 1 * time.Second
	}
	if cfg.ClickHouseAddr == "" {
		cfg.ClickHouseAddr = "localhost:9000"
	}
	if cfg.ClickHouseDB == "" {
		cfg.ClickHouseDB = "evc"
	}
	if cfg.ClickHouseUser == "" {
		cfg.ClickHouseUser = "evc"
	}
	if cfg.RedisAddr == "" {
		cfg.RedisAddr = "localhost:6379"
	}

	// 1. Connect to ClickHouse via native protocol
	chConn, err := clickhouse.Open(&clickhouse.Options{
		Addr: []string{cfg.ClickHouseAddr},
		Auth: clickhouse.Auth{
			Database: cfg.ClickHouseDB,
			Username: cfg.ClickHouseUser,
			Password: cfg.ClickHousePassword,
		},
		Settings: clickhouse.Settings{
			"max_execution_time": 60,
		},
		Compression: &clickhouse.Compression{
			Method: clickhouse.CompressionLZ4,
		},
		DialTimeout: 5 * time.Second,
	})
	if err != nil {
		return nil, fmt.Errorf("failed creating ClickHouse client: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := chConn.Ping(ctx); err != nil {
		log.Warn().Err(err).Str("addr", cfg.ClickHouseAddr).Msg("ClickHouse ping failed (will retry during service execution)")
	} else {
		log.Info().Str("addr", cfg.ClickHouseAddr).Msg("Connected to ClickHouse")
	}

	// 2. Connect to Redis
	rdb := redis.NewClient(&redis.Options{
		Addr:     cfg.RedisAddr,
		Password: cfg.RedisPassword,
		DB:       0,
	})
	if err := rdb.Ping(ctx).Err(); err != nil {
		log.Warn().Err(err).Str("addr", cfg.RedisAddr).Msg("Redis ping failed (will retry during service execution)")
	} else {
		log.Info().Str("addr", cfg.RedisAddr).Msg("Connected to Redis")
	}

	// 3. Kafka/Redpanda Consumer Client
	opts := []kgo.Opt{
		kgo.SeedBrokers(cfg.Brokers...),
		kgo.ConsumerGroup(cfg.ConsumerGroup),
		kgo.ConsumeTopics(cfg.CanonicalTopic),
		kgo.ConsumeResetOffset(kgo.NewOffset().AtStart()),
		kgo.FetchMaxBytes(50 * 1024 * 1024), // 50MB batch fetch
		kgo.DisableAutoCommit(),
	}

	client, err := kgo.NewClient(opts...)
	if err != nil {
		return nil, fmt.Errorf("failed creating Kafka consumer client: %w", err)
	}

	return &Service{
		cfg:         cfg,
		client:      client,
		chConn:      chConn,
		rdb:         rdb,
		stopChan:    make(chan struct{}),
		eventBuf:    make([]*canonical.Event, 0, cfg.BatchSize),
		latestByVIN: make(map[string]*canonical.Event),
		lastFlush:   time.Now(),
	}, nil
}

func (s *Service) Start(ctx context.Context) error {
	log.Info().
		Str("canonical_topic", s.cfg.CanonicalTopic).
		Str("consumer_group", s.cfg.ConsumerGroup).
		Int("batch_size", s.cfg.BatchSize).
		Dur("flush_interval", s.cfg.FlushInterval).
		Str("clickhouse", s.cfg.ClickHouseAddr).
		Str("redis", s.cfg.RedisAddr).
		Msg("Starting ingest sink service")

	defer func() {
		s.flushWithLock(context.Background())
		s.client.Close()
		s.chConn.Close()
		s.rdb.Close()
	}()

	flushTicker := time.NewTicker(s.cfg.FlushInterval)
	defer flushTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			return nil
		case <-s.stopChan:
			return nil
		case <-flushTicker.C:
			s.mu.Lock()
			if len(s.eventBuf) > 0 {
				if err := s.flushBatch(ctx); err != nil {
					log.Error().Err(err).Msg("Periodic flush error")
				}
			}
			s.mu.Unlock()
		default:
		}

		// Poll Kafka
		fetches := s.client.PollFetches(ctx)
		if fetches.IsClientClosed() {
			return nil
		}
		if errs := fetches.Errors(); len(errs) > 0 {
			for _, err := range errs {
				log.Warn().Err(err.Err).Str("topic", err.Topic).Int32("partition", err.Partition).Msg("Poll fetch error")
			}
		}

		var shouldFlush bool
		s.mu.Lock()
		iter := fetches.RecordIter()
		for !iter.Done() {
			record := iter.Next()
			var ev canonical.Event
			if err := json.Unmarshal(record.Value, &ev); err != nil {
				log.Warn().Err(err).Msg("Failed unmarshaling canonical record")
				continue
			}

			s.eventBuf = append(s.eventBuf, &ev)

			// Track latest event per VIN for Redis pipelining
			existing, exists := s.latestByVIN[ev.VIN]
			if !exists || ev.TS.After(existing.TS) || (ev.TS.Equal(existing.TS) && ev.Seq >= existing.Seq) {
				s.latestByVIN[ev.VIN] = &ev
			}

			if len(s.eventBuf) >= s.cfg.BatchSize {
				shouldFlush = true
			}
		}

		if shouldFlush || (len(s.eventBuf) > 0 && time.Since(s.lastFlush) >= s.cfg.FlushInterval) {
			if err := s.flushBatch(ctx); err != nil {
				log.Error().Err(err).Msg("Batch flush error")
			}
		}
		s.mu.Unlock()
	}
}

func (s *Service) Stop() {
	s.stopOnce.Do(func() {
		close(s.stopChan)
	})
}

func (s *Service) flushWithLock(ctx context.Context) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.eventBuf) > 0 {
		_ = s.flushBatch(ctx)
	}
}

// flushBatch inserts buffered events to ClickHouse, pipelines latest state to Redis, and commits Kafka offsets.
// MUST be called while holding s.mu.
func (s *Service) flushBatch(ctx context.Context) error {
	if len(s.eventBuf) == 0 {
		return nil
	}

	start := time.Now()
	events := s.eventBuf
	latestMap := s.latestByVIN

	// Reset buffers
	s.eventBuf = make([]*canonical.Event, 0, s.cfg.BatchSize)
	s.latestByVIN = make(map[string]*canonical.Event)
	s.lastFlush = time.Now()

	// 1. ClickHouse Native Batch Insert with Exponential Backoff Retry & Circuit Breaker
	if err := s.insertClickHouseWithRetry(ctx, events); err != nil {
		metrics.SinkErrorsTotal.WithLabelValues("clickhouse").Inc()
		log.Error().Err(err).Int("events", len(events)).Msg("ClickHouse batch insert failed after retries")
		return err
	}

	// 2. Redis Pipeline HSET latest (last per vin in batch)
	if err := s.pipelineRedisLatest(ctx, latestMap); err != nil {
		metrics.SinkErrorsTotal.WithLabelValues("redis").Inc()
		log.Warn().Err(err).Int("vins", len(latestMap)).Msg("Redis pipelined update failed")
		// Redis is AP/cache - we log error and increment metric, but continue
	}

	// 3. Record Metrics
	duration := time.Since(start).Seconds()
	metrics.SinkBatchSeconds.Observe(duration)
	metrics.RowsInsertedTotal.Add(float64(len(events)))

	// 4. Commit offsets only after durable writes complete
	commitCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := s.client.CommitUncommittedOffsets(commitCtx); err != nil {
		log.Warn().Err(err).Msg("Offset commit error after batch flush")
	}

	log.Debug().
		Int("rows", len(events)).
		Int("vins", len(latestMap)).
		Float64("duration_sec", duration).
		Msg("Flushed telemetry batch to ClickHouse and Redis")

	return nil
}

// insertClickHouseWithRetry executes a batch insert to ClickHouse with exponential backoff and circuit breaker pause
func (s *Service) insertClickHouseWithRetry(ctx context.Context, events []*canonical.Event) error {
	const maxRetries = 5
	backoff := 100 * time.Millisecond

	for attempt := 1; attempt <= maxRetries; attempt++ {
		batch, err := s.chConn.PrepareBatch(ctx, "INSERT INTO evc.telemetry (vin, ts, seq, oem, geohash7, lat, lon, speed_kmh, soc_pct, odo_km, batt_temp_c, charging, charge_kw, dtc, evt)")
		if err == nil {
			for _, e := range events {
				dtc := e.DTC
				if dtc == nil {
					dtc = []string{}
				}
				err = batch.Append(
					e.VIN,
					e.TS.UTC(),
					e.Seq,
					e.OEM,
					e.Geohash7,
					float32(e.Lat),
					float32(e.Lon),
					float32(e.SpeedKMH),
					float32(e.SOCPct),
					e.OdoKM,
					float32(e.BattTempC),
					uint8(e.Charging),
					float32(e.ChargeKW),
					dtc,
					e.Evt,
				)
				if err != nil {
					_ = batch.Abort()
					break
				}
			}

			if err == nil {
				if sendErr := batch.Send(); sendErr == nil {
					return nil // Success!
				} else {
					err = sendErr
				}
			}
		}

		log.Warn().
			Err(err).
			Int("attempt", attempt).
			Dur("backoff", backoff).
			Msg("ClickHouse batch insert failed, retrying...")

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(backoff):
		}
		backoff *= 2
	}

	// Circuit breaker: ClickHouse is unresponsive, wait for recovery
	log.Error().Msg("ClickHouse circuit breaker tripped: pausing consumption and waiting for health check recovery")
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			pingCtx, pingCancel := context.WithTimeout(context.Background(), 2*time.Second)
			if err := s.chConn.Ping(pingCtx); err == nil {
				pingCancel()
				log.Info().Msg("ClickHouse recovered, retrying batch insertion")
				return s.insertClickHouseWithRetry(ctx, events)
			}
			pingCancel()
		}
	}
}

// pipelineRedisLatest writes the latest telemetry state for each VIN in a single pipelined command batch
func (s *Service) pipelineRedisLatest(ctx context.Context, latestMap map[string]*canonical.Event) error {
	if len(latestMap) == 0 {
		return nil
	}

	pipe := s.rdb.Pipeline()
	for vin, ev := range latestMap {
		key := fmt.Sprintf("veh:latest:%s", vin)
		fields := map[string]interface{}{
			"vin":         ev.VIN,
			"ts":          ev.TS.UTC().Format(time.RFC3339),
			"seq":         ev.Seq,
			"oem":         ev.OEM,
			"lat":         ev.Lat,
			"lon":         ev.Lon,
			"geohash7":    ev.Geohash7,
			"speed_kmh":   ev.SpeedKMH,
			"soc_pct":     ev.SOCPct,
			"odo_km":      ev.OdoKM,
			"batt_temp_c": ev.BattTempC,
			"charging":    ev.Charging,
			"charge_kw":   ev.ChargeKW,
			"dtc":         strings.Join(ev.DTC, ","),
			"evt":         ev.Evt,
		}

		pipe.HSet(ctx, key, fields)
		pipe.Expire(ctx, key, 24*time.Hour)
	}

	pipeCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	_, err := pipe.Exec(pipeCtx)
	return err
}
