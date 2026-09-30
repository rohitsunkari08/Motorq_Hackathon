package producer

import (
	"context"
	"time"

	"github.com/rohitsunkari08/evc/services/simulator/pkg/generator"
	"github.com/rohitsunkari08/evc/services/simulator/pkg/metrics"
	"github.com/twmb/franz-go/pkg/kgo"
)

type Config struct {
	Brokers  []string
	Topic    string
	Linger   time.Duration
	BatchMax int32
}

type Producer struct {
	client *kgo.Client
	topic  string
}

func NewProducer(cfg Config) (*Producer, error) {
	if cfg.Topic == "" {
		cfg.Topic = "telemetry.raw"
	}
	if cfg.Linger == 0 {
		cfg.Linger = 5 * time.Millisecond
	}
	if cfg.BatchMax == 0 {
		cfg.BatchMax = 1024 * 1024 // 1MB
	}

	opts := []kgo.Opt{
		kgo.SeedBrokers(cfg.Brokers...),
		kgo.RequiredAcks(kgo.AllISRAcks()),
		kgo.ProducerLinger(cfg.Linger),
		kgo.ProducerBatchMaxBytes(cfg.BatchMax),
		kgo.ProducerBatchCompression(kgo.Lz4Compression()),
		kgo.MaxBufferedRecords(250_000),
	}

	client, err := kgo.NewClient(opts...)
	if err != nil {
		return nil, err
	}

	return &Producer{
		client: client,
		topic:  cfg.Topic,
	}, nil
}

func (p *Producer) Send(ctx context.Context, item generator.PayloadResult, callback func(err error)) {
	record := &kgo.Record{
		Topic: p.topic,
		Key:   []byte(item.VIN),
		Value: item.Payload,
		Headers: []kgo.RecordHeader{
			{Key: "oem", Value: []byte(item.OEM)},
		},
	}

	metrics.EventsSentTotal.Inc()

	p.client.Produce(ctx, record, func(r *kgo.Record, err error) {
		if callback != nil {
			callback(err)
		}
	})
}

func (p *Producer) Flush(ctx context.Context) error {
	return p.client.Flush(ctx)
}

func (p *Producer) Close() {
	p.client.Close()
}
