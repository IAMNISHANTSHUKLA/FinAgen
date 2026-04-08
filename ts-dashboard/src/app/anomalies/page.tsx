export default function AnomaliesPage() {
  const anomalies = [
    { id: '1', ticker: 'GME', type: 'VOLUME_SPIKE', risk: 0.89, desc: 'Volume surged to 8.5x 30-day average — potential short squeeze activity', action: 'Trigger real-time monitoring, alert risk desk', severity: 'critical', time: '3 min ago' },
    { id: '2', ticker: 'TSLA', type: 'DAILY_CRASH', risk: 0.72, desc: 'Single-day drop of -12.3% following earnings miss', action: 'Review portfolio exposure, consider hedging', severity: 'high', time: '18 min ago' },
    { id: '3', ticker: 'NVDA', type: 'VOLUME_SPIKE', risk: 0.61, desc: 'Volume 4.2x average ahead of product announcement', action: 'Monitor for insider trading signals', severity: 'medium', time: '42 min ago' },
    { id: '4', ticker: 'COIN', type: 'HIGH_RISK_ACTIVITY', risk: 0.78, desc: 'High-risk ticker showing unusual options activity with +340% IV surge', action: 'Review crypto exposure, assess correlated assets', severity: 'high', time: '1 hr ago' },
    { id: '5', ticker: 'JPM', type: 'RECURRING_CHANGE', risk: 0.35, desc: 'Dividend payout increased by 22% vs previous quarter', action: 'No immediate action — positive signal', severity: 'low', time: '2 hr ago' },
  ];

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Anomaly Feed</h1>
        <p className="page-subtitle">Real-time risk alerts from Kafka event stream with confidence scores</p>
      </div>

      <div className="kpi-grid" style={{ marginBottom: 24 }}>
        <div className="kpi-card">
          <div className="kpi-label">Active Alerts</div>
          <div className="kpi-value" style={{ color: 'var(--accent-red)' }}>5</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Critical</div>
          <div className="kpi-value" style={{ color: 'var(--accent-red)' }}>1</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Avg Risk Score</div>
          <div className="kpi-value" style={{ color: 'var(--accent-amber)' }}>0.67</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Tickers Monitored</div>
          <div className="kpi-value" style={{ color: 'var(--accent-cyan)' }}>15</div>
        </div>
      </div>

      {anomalies.map((a) => (
        <div key={a.id} className={`anomaly-card ${a.severity}`}>
          <div className="anomaly-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span className="anomaly-ticker">{a.ticker}</span>
              <span className="anomaly-type">{a.type}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span className={`confidence-badge ${a.risk > 0.7 ? 'low' : a.risk > 0.5 ? 'medium' : 'high'}`}>
                Risk: {a.risk.toFixed(2)}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{a.time}</span>
            </div>
          </div>
          <div className="anomaly-description">{a.desc}</div>
          <div className="anomaly-action">→ {a.action}</div>
        </div>
      ))}
    </>
  );
}
