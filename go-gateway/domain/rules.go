package domain

import "fmt"

// AnomalyRule defines an interface for pluggable anomaly detection rules.
// Open/Closed: add new rules without modifying the detector.
type AnomalyRule interface {
	Name() string
	Evaluate(event TransactionEvent) (bool, float64, string)
	// Returns: (triggered, riskScore, description)
}

// SpikeRule detects volume spikes > threshold * 30-day average.
type SpikeRule struct {
	ThresholdMultiplier float64
}

func (r *SpikeRule) Name() string { return "VOLUME_SPIKE" }

func (r *SpikeRule) Evaluate(event TransactionEvent) (bool, float64, string) {
	if event.VolumeVs30DAvg > r.ThresholdMultiplier {
		risk := minF(1.0, event.VolumeVs30DAvg/10.0)
		desc := "Volume spike detected: " + event.Ticker +
			" volume is " + formatFloat(event.VolumeVs30DAvg) + "x 30-day average"
		return true, risk, desc
	}
	return false, 0, ""
}

// RecurringChangeRule detects recurring charge changes > threshold%.
type RecurringChangeRule struct {
	ThresholdPct float64
}

func (r *RecurringChangeRule) Name() string { return "RECURRING_CHANGE" }

func (r *RecurringChangeRule) Evaluate(event TransactionEvent) (bool, float64, string) {
	deviation := absF(event.PriceDeviation30Pct)
	if deviation > r.ThresholdPct {
		risk := minF(1.0, deviation/50.0)
		desc := "Price deviation detected: " + event.Ticker +
			" deviates " + formatFloat(deviation) + "% from 30-day average"
		return true, risk, desc
	}
	return false, 0, ""
}

// HighRiskMerchantRule flags activity from high-risk tickers.
type HighRiskMerchantRule struct{}

func (r *HighRiskMerchantRule) Name() string { return "HIGH_RISK_ACTIVITY" }

func (r *HighRiskMerchantRule) Evaluate(event TransactionEvent) (bool, float64, string) {
	if event.HighRisk && (event.VolumeVs30DAvg > 2.0 || absF(event.DailyReturnPct) > 5.0) {
		risk := minF(1.0, 0.6+absF(event.DailyReturnPct)/20.0)
		desc := "High-risk ticker activity: " + event.Ticker +
			" with " + formatFloat(absF(event.DailyReturnPct)) + "% daily return"
		return true, risk, desc
	}
	return false, 0, ""
}

// DailyCrashRule detects single-day crashes/surges > threshold%.
type DailyCrashRule struct {
	ThresholdPct float64
}

func (r *DailyCrashRule) Name() string { return "DAILY_CRASH_SURGE" }

func (r *DailyCrashRule) Evaluate(event TransactionEvent) (bool, float64, string) {
	if absF(event.DailyReturnPct) > r.ThresholdPct {
		direction := "surge"
		if event.DailyReturnPct < 0 {
			direction = "crash"
		}
		risk := minF(1.0, absF(event.DailyReturnPct)/30.0)
		desc := "Daily " + direction + " detected: " + event.Ticker +
			" moved " + formatFloat(event.DailyReturnPct) + "%"
		return true, risk, desc
	}
	return false, 0, ""
}

// ─── Helper Functions ───

func absF(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}

func minF(a, b float64) float64 {
	if a < b {
		return a
	}
	return b
}

func formatFloat(f float64) string {
	return fmt.Sprintf("%.2f", f)
}
