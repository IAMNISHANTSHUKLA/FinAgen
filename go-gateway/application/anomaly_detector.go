package application

import (
	"time"

	"github.com/finagentx/go-gateway/domain"
	"github.com/google/uuid"
)

// AnomalyDetector runs all registered rules against incoming events.
type AnomalyDetector struct {
	rules []domain.AnomalyRule
}

// NewAnomalyDetector creates a detector with default financial rules.
func NewAnomalyDetector() *AnomalyDetector {
	return &AnomalyDetector{
		rules: []domain.AnomalyRule{
			&domain.SpikeRule{ThresholdMultiplier: 3.0},
			&domain.RecurringChangeRule{ThresholdPct: 15.0},
			&domain.HighRiskMerchantRule{},
			&domain.DailyCrashRule{ThresholdPct: 10.0},
		},
	}
}

// Detect evaluates all rules and returns any triggered anomalies.
func (d *AnomalyDetector) Detect(event domain.TransactionEvent) []domain.AnomalyEvent {
	var anomalies []domain.AnomalyEvent

	for _, rule := range d.rules {
		triggered, riskScore, description := rule.Evaluate(event)
		if triggered {
			anomalies = append(anomalies, domain.AnomalyEvent{
				AlertID:     uuid.New().String()[:12],
				Ticker:      event.Ticker,
				AlertType:   rule.Name(),
				RiskScore:   riskScore,
				Description: description,
				Source:      event,
				Action:      "Monitor and review",
				Timestamp:   time.Now(),
			})
		}
	}

	return anomalies
}

// AddRule adds a custom anomaly detection rule.
func (d *AnomalyDetector) AddRule(rule domain.AnomalyRule) {
	d.rules = append(d.rules, rule)
}
