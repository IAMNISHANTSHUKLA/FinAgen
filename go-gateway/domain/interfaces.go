package domain

import "context"

// EventConsumer consumes events from a message broker.
type EventConsumer interface {
	Start(ctx context.Context) error
	Stop() error
}

// AuditStorage stores audit entries to persistent storage.
type AuditStorage interface {
	Append(entry AuditEntry) error
	Verify(sessionID string) (bool, error)
}

// AgentClient communicates with the Python AI Core service.
type AgentClient interface {
	SubmitQuery(ctx context.Context, sessionID, query, userID string) (map[string]interface{}, error)
	GetTrace(ctx context.Context, sessionID string) (map[string]interface{}, error)
}

// MetricsCollector collects metrics for observability.
type MetricsCollector interface {
	RecordLatency(operation string, durationMs int64)
	RecordError(operation string, errType string)
	RecordAnomaly(alertType string)
}
