export default function TracesPage() {
  const mockSteps = [
    { id: '1', tool: 'analyze_spend', input: '{"ticker":"AAPL","period":"Q3 2024"}', output: '{"revenue":"$89.5B","net_income":"$22.9B"}', latency: 1200, confidence: 0.92, reasoning: 'User asked about AAPL revenue — calling analyze_spend with Q3 2024 period.' },
    { id: '2', tool: 'detect_anomaly', input: '{"ticker":"AAPL","lookback_days":30}', output: '{"anomalies_found":2,"risk_score":0.45}', latency: 800, confidence: 0.87, reasoning: 'Checking for anomalies to provide complete risk context alongside financial analysis.' },
    { id: '3', tool: 'generate_report', input: '{"ticker":"AAPL","report_type":"comprehensive"}', output: '{"title":"AAPL Q3 2024 Report","sections":4}', latency: 1500, confidence: 0.91, reasoning: 'Compiling all data into a comprehensive report with citations.' },
  ];

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Agent Trace Viewer</h1>
        <p className="page-subtitle">Step-by-step reasoning visualization with tool calls and outputs</p>
      </div>

      <div className="glass-card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Session: abc123def456</div>
            <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: 4 }}>{"What was AAPL's revenue in Q3 2024?"}</div>
          </div>
          <span className="confidence-badge high">Confidence: 0.92</span>
        </div>
        <div style={{ display: 'flex', gap: 24, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <span>Intent: <strong style={{ color: 'var(--accent-cyan)' }}>spend_analysis</strong></span>
          <span>Total Latency: <strong>3.5s</strong></span>
          <span>Tools: <strong>3</strong></span>
          <span>Citations: <strong>5</strong></span>
        </div>
      </div>

      <div className="trace-timeline">
        {mockSteps.map((step, i) => (
          <div key={step.id} className="trace-step" style={{ animationDelay: `${i * 0.1}s` }}>
            <div className="trace-step-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 700 }}>Step {i + 1}</span>
                <span className="trace-tool-name">{step.tool}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <span className="confidence-badge high">{step.confidence}</span>
                <span className="trace-latency">{step.latency}ms</span>
              </div>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: 8, fontStyle: 'italic' }}>
              💭 {step.reasoning}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Input</div>
                <div className="code-block">{step.input}</div>
              </div>
              <div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Output</div>
                <div className="code-block">{step.output}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
