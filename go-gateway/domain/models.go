// Package domain contains core domain types for the Go gateway.
// Zero external dependencies — pure Go types.
package domain

import "time"

// TransactionEvent represents a market transaction from Kafka.
type TransactionEvent struct {
	EventID             string            `json:"event_id"`
	Ticker              string            `json:"ticker"`
	Date                string            `json:"date"`
	Open                float64           `json:"open"`
	High                float64           `json:"high"`
	Low                 float64           `json:"low"`
	Close               float64           `json:"close"`
	Volume              int64             `json:"volume"`
	DailyReturnPct      float64           `json:"daily_return_pct"`
	VolumeVs30DAvg      float64           `json:"volume_vs_30d_avg"`
	PriceDeviation30Pct float64           `json:"price_deviation_30d_pct"`
	Sector              string            `json:"sector"`
	Industry            string            `json:"industry"`
	HighRisk            bool              `json:"high_risk"`
	AnomalyFlags        []string          `json:"anomaly_flags"`
	Metadata            map[string]string `json:"metadata"`
}

// AnomalyEvent is emitted when an anomaly rule fires.
type AnomalyEvent struct {
	AlertID     string           `json:"alert_id"`
	Ticker      string           `json:"ticker"`
	AlertType   string           `json:"alert_type"`
	RiskScore   float64          `json:"risk_score"`
	Description string           `json:"description"`
	Source      TransactionEvent `json:"source_event"`
	Action      string           `json:"recommended_action"`
	Timestamp   time.Time        `json:"timestamp"`
}

// AuditEntry represents an append-only audit log entry with hash chain.
type AuditEntry struct {
	Timestamp  time.Time `json:"ts"`
	SessionID  string    `json:"session_id"`
	UserID     string    `json:"user_id"`
	Action     string    `json:"action"`
	ToolCalled string    `json:"tool"`
	Input      string    `json:"input"`
	Output     string    `json:"output"`
	Confidence float64   `json:"confidence"`
	PrevHash   string    `json:"prev_hash"`
	Hash       string    `json:"hash"`
}

// ProcessResult is the result of processing a transaction event.
type ProcessResult struct {
	Event     TransactionEvent `json:"event"`
	Anomalies []AnomalyEvent  `json:"anomalies"`
	Error     error            `json:"-"`
}
