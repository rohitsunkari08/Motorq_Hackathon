package normalizer

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"sync"
	"time"

	"github.com/rs/zerolog/log"
	"github.com/twmb/franz-go/pkg/kgo"

	"github.com/rohitsunkari08/evc/services/ingest/pkg/adapters"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/dedupe"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/metrics"
	"github.com/rohitsunkari08/evc/services/ingest/pkg/validation"
)

type DLQEnvelope struct {
	Reason     string `json:"reason"`
	Error      string `json:"error"`
	OEM        string `json:"oem,omitempty"`
	Raw        string `json:"raw"`
	ReceivedAt string `json:"received_at"`
}

type Config struct {
	Brokers        []string
	RawTopic       string
	CanonicalTopic string
	DLQTopic       string
	ConsumerGroup  string
	BatchSize      int
	NumWorkers     int
}

type Service struct {
	cfg      Config
	client   *kgo.Client
	registry *adapters.Registry
	deduper  *dedupe.PartitionBloomDeduper
	stopOnce sync.Once
	stopChan chan struct{}
}

func NewService(cfg Config) (*Service, error) {
	if cfg.RawTopic == "" {
		cfg.RawTopic = "telemetry.raw"
	}
	if cfg.CanonicalTopic == "" {
		cfg.CanonicalTopic = "telemetry.canonical"
	}
	if cfg.DLQTopic == "" {
		cfg.DLQTopic = "telemetry.dlq"
	}
	if cfg.ConsumerGroup == "" {
		cfg.ConsumerGroup = "ingest-normalize-group"
	}
	if cfg.BatchSize <= 0 {
		cfg.BatchSize = 10000
	}
	if cfg.NumWorkers <= 0 {
		cfg.NumWorkers = 16
	}

	opts := []kgo.Opt{
		kgo.SeedBrokers(cfg.Brokers...),
		kgo.ConsumerGroup(cfg.ConsumerGroup),
		kgo.ConsumeTopics(cfg.RawTopic),
		kgo.ConsumeResetOffset(kgo.NewOffset().AtStart()),
		kgo.FetchMaxBytes(50 * 1024 * 1024), // 50MB batch fetch
		kgo.RequiredAcks(kgo.AllISRAcks()),
		kgo.ProducerBatchMaxBytes(1024 * 1024),
		kgo.ProducerLinger(5 * time.Millisecond),
	}

	client, err := kgo.NewClient(opts...)
	if err != nil {
		return nil, err
	}

	return &Service{
		cfg:      cfg,
		client:   client,
		registry: adapters.DefaultRegistry,
		deduper:  dedupe.NewPartitionBloomDeduper(10_000_000, 0.001),
		stopChan: make(chan struct{}),
	}, nil
}

func (s *Service) Start(ctx context.Context) error {
	log.Info().
		Str("raw_topic", s.cfg.RawTopic).
		Str("canonical_topic", s.cfg.CanonicalTopic).
		Str("dlq_topic", s.cfg.DLQTopic).
		Msg("Starting ingest normalizer service")

	recordChan := make(chan *kgo.Record, s.cfg.BatchSize*2)
	var wg sync.WaitGroup

	// Launch partition-parallel worker pool
	for i := 0; i < s.cfg.NumWorkers; i++ {
		wg.Add(1)
		go func(workerID int) {
			defer wg.Done()
			s.worker(ctx, recordChan)
		}(i)
	}

	defer func() {
		close(recordChan)
		wg.Wait()
		s.client.Close()
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
				log.Warn().Err(err.Err).Str("topic", err.Topic).Int32("partition", err.Partition).Msg("Poll fetch error")
			}
		}

		iter := fetches.RecordIter()
		for !iter.Done() {
			record := iter.Next()
			select {
			case recordChan <- record:
			case <-ctx.Done():
				return nil
			case <-s.stopChan:
				return nil
			}
		}

		// Commit offsets after batch is accepted
		if err := s.client.CommitUncommittedOffsets(ctx); err != nil {
			log.Warn().Err(err).Msg("Commit offset error")
		}
	}
}

func (s *Service) Stop() {
	s.stopOnce.Do(func() {
		close(s.stopChan)
	})
}

func (s *Service) worker(ctx context.Context, records <-chan *kgo.Record) {
	for rec := range records {
		s.ProcessRecord(ctx, rec)
	}
}

// ProcessRecord normalizes a single raw record, routing to canonical topic, DLQ, or dropping duplicates.
func (s *Service) ProcessRecord(ctx context.Context, rec *kgo.Record) {
	start := time.Now()
	defer func() {
		metrics.NormalizeLatency.Observe(time.Since(start).Seconds())
	}()

	// Extract OEM hint from headers if present
	oemHint := ""
	for _, h := range rec.Headers {
		if strings.EqualFold(h.Key, "oem") {
			oemHint = string(h.Value)
			break
		}
	}

	// 1. Adapter Parse
	event, err := s.registry.DetectAndParse(oemHint, rec.Value)
	if err != nil {
		reason := "parse_error"
		if errors.Is(err, adapters.ErrUnknownOEM) {
			reason = "unknown_oem"
		}
		metrics.InvalidTotal.WithLabelValues(reason).Inc()
		s.sendToDLQ(ctx, rec, reason, err.Error(), oemHint)
		return
	}

	// 2. Validate Canonical Event
	if err := event.Validate(); err != nil {
		reason := "validation_error"
		if errors.Is(err, validation.ErrInvalidVINChecksum) || errors.Is(err, validation.ErrInvalidVINFormat) {
			reason = "bad_vin"
		} else if errors.Is(err, validation.ErrInvalidSOC) || errors.Is(err, validation.ErrInvalidSpeed) ||
			errors.Is(err, validation.ErrInvalidBatteryTemp) || errors.Is(err, validation.ErrInvalidCoordinates) {
			reason = "range_violation"
		} else if errors.Is(err, validation.ErrFutureTimestamp) {
			reason = "future_timestamp"
		} else if errors.Is(err, validation.ErrInvalidDTC) {
			reason = "bad_dtc"
		}
		metrics.InvalidTotal.WithLabelValues(reason).Inc()
		s.sendToDLQ(ctx, rec, reason, err.Error(), event.OEM)
		return
	}

	// 3. Bloom Deduplication per partition on (vin, seq)
	if s.deduper.IsDuplicate(rec.Partition, event.VIN, event.Seq) {
		metrics.DedupeDroppedTotal.Inc()
		return
	}

	// 4. Produce to Canonical Topic
	payload, err := json.Marshal(event)
	if err != nil {
		log.Error().Err(err).Msg("Failed to serialize canonical event")
		return
	}

	metrics.IngestEventsTotal.WithLabelValues(event.OEM).Inc()

	outRecord := &kgo.Record{
		Topic: s.cfg.CanonicalTopic,
		Key:   []byte(event.VIN),
		Value: payload,
	}

	s.client.Produce(ctx, outRecord, func(r *kgo.Record, err error) {
		if err != nil {
			log.Error().Err(err).Str("vin", event.VIN).Msg("Failed producing canonical record")
		}
	})
}

func (s *Service) sendToDLQ(ctx context.Context, rec *kgo.Record, reason string, errMsg string, oem string) {
	dlqData := DLQEnvelope{
		Reason:     reason,
		Error:      errMsg,
		OEM:        oem,
		Raw:        string(rec.Value),
		ReceivedAt: time.Now().UTC().Format(time.RFC3339),
	}

	dlqBytes, err := json.Marshal(dlqData)
	if err != nil {
		log.Error().Err(err).Msg("Failed to marshal DLQ envelope")
		return
	}

	outRecord := &kgo.Record{
		Topic: s.cfg.DLQTopic,
		Key:   rec.Key,
		Value: dlqBytes,
	}

	s.client.Produce(ctx, outRecord, func(r *kgo.Record, err error) {
		if err != nil {
			log.Error().Err(err).Msg("Failed producing to DLQ")
		}
	})
}
