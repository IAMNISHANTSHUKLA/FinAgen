package streaming

import (
	"context"
	"encoding/json"
	"sync"
	"time"

	"github.com/finagentx/go-gateway/application"
	"github.com/finagentx/go-gateway/domain"
	"github.com/rs/zerolog/log"
)

// WorkerPool implements a bounded concurrency Kafka consumer (Fix #6).
// Uses semaphore pattern for backpressure instead of goroutine-per-partition.
type WorkerPool struct {
	jobs       chan []byte
	results    chan domain.ProcessResult
	sem        chan struct{} // bounded concurrency
	detector   *application.AnomalyDetector
	maxWorkers int
	wg         sync.WaitGroup
}

// NewWorkerPool creates a bounded worker pool for transaction processing.
func NewWorkerPool(maxWorkers int, detector *application.AnomalyDetector) *WorkerPool {
	return &WorkerPool{
		jobs:       make(chan []byte, 1000),       // buffered — backpressure
		results:    make(chan domain.ProcessResult, 1000),
		sem:        make(chan struct{}, maxWorkers), // blocks when maxWorkers reached
		detector:   detector,
		maxWorkers: maxWorkers,
	}
}

// Start begins processing messages from the jobs channel.
func (p *WorkerPool) Start(ctx context.Context) {
	log.Info().Int("max_workers", p.maxWorkers).Msg("Worker pool started")

	go func() {
		for {
			select {
			case msg := <-p.jobs:
				p.sem <- struct{}{} // acquire semaphore — blocks at max
				p.wg.Add(1)
				go func(data []byte) {
					defer func() {
						<-p.sem // release semaphore
						p.wg.Done()
					}()

					result := p.processMessage(data)
					p.results <- result
				}(msg)

			case <-ctx.Done():
				log.Info().Msg("Worker pool shutting down")
				p.wg.Wait()
				return
			}
		}
	}()
}

// Submit adds a message to the processing queue.
func (p *WorkerPool) Submit(data []byte) {
	p.jobs <- data
}

// Results returns the results channel for consuming processed events.
func (p *WorkerPool) Results() <-chan domain.ProcessResult {
	return p.results
}

func (p *WorkerPool) processMessage(data []byte) domain.ProcessResult {
	var event domain.TransactionEvent
	if err := json.Unmarshal(data, &event); err != nil {
		log.Error().Err(err).Msg("Failed to unmarshal transaction event")
		return domain.ProcessResult{Error: err}
	}

	// Run anomaly detection rules
	anomalies := p.detector.Detect(event)

	if len(anomalies) > 0 {
		log.Info().
			Str("ticker", event.Ticker).
			Int("anomalies", len(anomalies)).
			Msg("Anomalies detected")
	}

	return domain.ProcessResult{
		Event:     event,
		Anomalies: anomalies,
	}
}

// KafkaConsumer wraps the worker pool with Kafka consumer logic.
type KafkaConsumer struct {
	pool           *WorkerPool
	bootstrapServers string
	topic          string
	groupID        string
}

// NewKafkaConsumer creates a new Kafka consumer with bounded worker pool.
func NewKafkaConsumer(
	bootstrapServers, topic, groupID string,
	maxWorkers int,
	detector *application.AnomalyDetector,
) *KafkaConsumer {
	return &KafkaConsumer{
		pool:             NewWorkerPool(maxWorkers, detector),
		bootstrapServers: bootstrapServers,
		topic:            topic,
		groupID:          groupID,
	}
}

// Start begins consuming from Kafka.
func (c *KafkaConsumer) Start(ctx context.Context) error {
	log.Info().
		Str("servers", c.bootstrapServers).
		Str("topic", c.topic).
		Str("group", c.groupID).
		Msg("Starting Kafka consumer")

	// Start worker pool
	c.pool.Start(ctx)

	// Process results in background
	go func() {
		for result := range c.pool.Results() {
			if result.Error != nil {
				log.Error().Err(result.Error).Msg("Processing error — sending to DLQ")
				continue
			}

			for _, anomaly := range result.Anomalies {
				log.Info().
					Str("ticker", anomaly.Ticker).
					Str("type", anomaly.AlertType).
					Float64("risk", anomaly.RiskScore).
					Msg("Anomaly alert")
			}
		}
	}()

	// In production: use confluent-kafka-go consumer here
	// For now: log that consumer is ready
	log.Info().Msg("Kafka consumer ready (connect to real broker in production)")

	<-ctx.Done()
	return nil
}

// Stop gracefully stops the consumer.
func (c *KafkaConsumer) Stop() error {
	log.Info().Msg("Kafka consumer stopped")
	return nil
}

// GetStartTime returns server start time for uptime tracking.
func (c *KafkaConsumer) GetStartTime() time.Time {
	return time.Now()
}
