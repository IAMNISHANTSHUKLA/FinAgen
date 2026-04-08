export default function OverviewPage() {
  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Dashboard Overview</h1>
        <p className="page-subtitle">Real-time operational metrics and system health</p>
      </div>

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Total Queries</div>
          <div className="kpi-value" style={{ color: 'var(--accent-blue)' }}>1,247</div>
          <div className="kpi-trend positive">↑ 12.3% vs last week</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Anomalies Detected</div>
          <div className="kpi-value" style={{ color: 'var(--accent-amber)' }}>38</div>
          <div className="kpi-trend negative">↑ 5.2% vs last week</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Avg Latency</div>
          <div className="kpi-value" style={{ color: 'var(--accent-cyan)' }}>2.3s</div>
          <div className="kpi-trend positive">↓ 18% vs last week</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Hallucination Rate</div>
          <div className="kpi-value" style={{ color: 'var(--accent-green)' }}>3.2%</div>
          <div className="kpi-trend positive">↓ 0.8% vs last week</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Cache Hit Rate</div>
          <div className="kpi-value" style={{ color: 'var(--accent-purple)' }}>67%</div>
          <div className="kpi-trend positive">↑ 4.1% vs last week</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Feedback Score</div>
          <div className="kpi-value" style={{ color: 'var(--accent-green)' }}>4.2</div>
          <div className="kpi-trend positive">↑ 0.3 vs last week</div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="glass-card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 16 }}>Recent Agent Activity</h2>
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Query</th>
              <th>Intent</th>
              <th>Tools Used</th>
              <th>Confidence</th>
              <th>Latency</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>2 min ago</td>
              <td>AAPL revenue analysis Q3 2024</td>
              <td><span className="anomaly-type">spend_analysis</span></td>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>analyze_spend, generate_report</td>
              <td><span className="confidence-badge high">0.92</span></td>
              <td style={{ fontFamily: 'var(--font-mono)' }}>1.8s</td>
            </tr>
            <tr>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>5 min ago</td>
              <td>TSLA volume anomalies last 30 days</td>
              <td><span className="anomaly-type">anomaly</span></td>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>detect_anomaly</td>
              <td><span className="confidence-badge high">0.87</span></td>
              <td style={{ fontFamily: 'var(--font-mono)' }}>2.1s</td>
            </tr>
            <tr>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>12 min ago</td>
              <td>Compare MSFT and GOOGL margins</td>
              <td><span className="anomaly-type">comparison</span></td>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>analyze_spend ×2</td>
              <td><span className="confidence-badge medium">0.73</span></td>
              <td style={{ fontFamily: 'var(--font-mono)' }}>3.4s</td>
            </tr>
            <tr>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>18 min ago</td>
              <td>GME high-risk activity assessment</td>
              <td><span className="anomaly-type">anomaly</span></td>
              <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>detect_anomaly, recommend_action</td>
              <td><span className="confidence-badge low">0.58</span></td>
              <td style={{ fontFamily: 'var(--font-mono)' }}>4.7s</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* System Health */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div className="glass-card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Retrieval Performance</h3>
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Precision@5</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>0.82</span>
            </div>
            <div className="metric-bar"><div className="metric-fill good" style={{ width: '82%' }} /></div>
          </div>
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Recall@10</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>0.91</span>
            </div>
            <div className="metric-bar"><div className="metric-fill good" style={{ width: '91%' }} /></div>
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
              <span style={{ color: 'var(--text-muted)' }}>Faithfulness</span>
              <span style={{ fontFamily: 'var(--font-mono)' }}>0.94</span>
            </div>
            <div className="metric-bar"><div className="metric-fill good" style={{ width: '94%' }} /></div>
          </div>
        </div>

        <div className="glass-card">
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Tool Usage Distribution</h3>
          <div style={{ fontSize: '0.85rem' }}>
            {[
              { name: 'analyze_spend', pct: 42, color: 'var(--accent-blue)' },
              { name: 'detect_anomaly', pct: 28, color: 'var(--accent-amber)' },
              { name: 'generate_report', pct: 20, color: 'var(--accent-purple)' },
              { name: 'recommend_action', pct: 10, color: 'var(--accent-red)' },
            ].map((tool) => (
              <div key={tool.name} style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>{tool.name}</span>
                  <span style={{ color: 'var(--text-muted)' }}>{tool.pct}%</span>
                </div>
                <div className="metric-bar">
                  <div style={{ height: '100%', width: `${tool.pct}%`, background: tool.color, borderRadius: 4, transition: 'width 0.8s ease' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
