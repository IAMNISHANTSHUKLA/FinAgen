export default function FeedbackPage() {
  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Feedback & Active Learning</h1>
        <p className="page-subtitle">Human-in-the-loop feedback collection and low-confidence query review</p>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-label">Total Feedback</div>
          <div className="kpi-value" style={{ color: 'var(--accent-blue)' }}>142</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Satisfaction Rate</div>
          <div className="kpi-value" style={{ color: 'var(--accent-green)' }}>87%</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Corrections</div>
          <div className="kpi-value" style={{ color: 'var(--accent-amber)' }}>12</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Pending Review</div>
          <div className="kpi-value" style={{ color: 'var(--accent-red)' }}>5</div>
        </div>
      </div>

      <div className="glass-card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>⚠️ Low-Confidence Queries (Need Review)</h3>
        {[
          { query: "GME insider trading indicators Q4", confidence: 0.42, time: "1 hr ago" },
          { query: "Predict NVDA stock price next quarter", confidence: 0.31, time: "3 hr ago" },
          { query: "SVB bankruptcy cause analysis", confidence: 0.48, time: "5 hr ago" },
        ].map((q, i) => (
          <div key={i} className="anomaly-card medium" style={{ borderLeftColor: 'var(--accent-amber)' }}>
            <div className="anomaly-header">
              <span style={{ fontWeight: 600 }}>{q.query}</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <span className="confidence-badge low">Conf: {q.confidence}</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{q.time}</span>
              </div>
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" style={{ fontSize: '0.75rem', padding: '6px 12px' }}>✓ Approve</button>
              <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '6px 12px' }}>✎ Correct</button>
              <button className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '6px 12px' }}>✕ Reject</button>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
