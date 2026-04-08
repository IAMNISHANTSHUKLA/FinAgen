package resilience

import (
	"time"

	"github.com/rs/zerolog/log"
	"github.com/sony/gobreaker"
)

// NewAICoreBreaker creates a circuit breaker for Python AI Core calls.
// OPEN after 5 consecutive failures, half-open probe after 30s.
func NewAICoreBreaker() *gobreaker.CircuitBreaker {
	return gobreaker.NewCircuitBreaker(gobreaker.Settings{
		Name:        "ai-core",
		MaxRequests: 3,                     // half-open: allow 3 probe requests
		Interval:    10 * time.Second,      // reset failure count after interval
		Timeout:     30 * time.Second,      // time in open state before half-open
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			return counts.ConsecutiveFailures > 5
		},
		OnStateChange: func(name string, from gobreaker.State, to gobreaker.State) {
			log.Warn().
				Str("breaker", name).
				Str("from", from.String()).
				Str("to", to.String()).
				Msg("Circuit breaker state change")
		},
	})
}
