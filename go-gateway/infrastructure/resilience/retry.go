package resilience

import (
	"context"
	"math"
	"math/rand"
	"time"

	"github.com/rs/zerolog/log"
)

// RetryConfig configures retry behavior.
type RetryConfig struct {
	MaxRetries     int
	BaseDelay      time.Duration
	MaxDelay       time.Duration
	BackoffFactor  float64
	JitterFraction float64 // 0.0-1.0
}

// DefaultRetryConfig returns sensible defaults.
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{
		MaxRetries:     3,
		BaseDelay:      100 * time.Millisecond,
		MaxDelay:       10 * time.Second,
		BackoffFactor:  2.0,
		JitterFraction: 0.3,
	}
}

// RetryWithBackoff executes a function with exponential backoff and jitter.
func RetryWithBackoff(ctx context.Context, cfg RetryConfig, operation string, fn func() error) error {
	var lastErr error

	for attempt := 0; attempt <= cfg.MaxRetries; attempt++ {
		if err := fn(); err == nil {
			if attempt > 0 {
				log.Info().
					Str("operation", operation).
					Int("attempt", attempt+1).
					Msg("Retry succeeded")
			}
			return nil
		} else {
			lastErr = err
		}

		if attempt == cfg.MaxRetries {
			break
		}

		// Calculate delay with exponential backoff + jitter
		delay := float64(cfg.BaseDelay) * math.Pow(cfg.BackoffFactor, float64(attempt))
		if delay > float64(cfg.MaxDelay) {
			delay = float64(cfg.MaxDelay)
		}

		// Add jitter
		jitter := delay * cfg.JitterFraction * (rand.Float64()*2 - 1)
		actualDelay := time.Duration(delay + jitter)

		log.Warn().
			Str("operation", operation).
			Int("attempt", attempt+1).
			Dur("delay", actualDelay).
			Err(lastErr).
			Msg("Retrying after failure")

		select {
		case <-time.After(actualDelay):
		case <-ctx.Done():
			return ctx.Err()
		}
	}

	return lastErr
}
