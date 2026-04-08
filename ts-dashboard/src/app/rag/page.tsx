export default function RAGPage() {
  const chunks = [
    { id: 'chunk-a1b2c3', docId: 'AAPL-income-20240930', text: 'Apple Inc Income Statement for period ending 2024-09-30:\n  Total Revenue: $89.50B\n  Net Income: $22.96B\n  Operating Income: $29.59B', ticker: 'AAPL', type: 'income_statement', score: 0.94, cited: true },
    { id: 'chunk-d4e5f6', docId: 'AAPL-income-20240630', text: 'Apple Inc Income Statement for period ending 2024-06-30:\n  Total Revenue: $85.78B\n  Net Income: $21.45B\n  Operating Margin: 30.1%', ticker: 'AAPL', type: 'income_statement', score: 0.87, cited: true },
    { id: 'chunk-g7h8i9', docId: 'AAPL-balance-20240930', text: 'Apple Inc Balance Sheet:\n  Total Assets: $352.58B\n  Total Liabilities: $290.44B\n  Shareholders Equity: $62.15B', ticker: 'AAPL', type: 'balance_sheet', score: 0.72, cited: false },
    { id: 'chunk-j0k1l2', docId: 'AAPL-cashflow-20240930', text: 'Apple Inc Cash Flow:\n  Operating Cash Flow: $26.81B\n  Capital Expenditures: -$2.91B\n  Free Cash Flow: $23.90B', ticker: 'AAPL', type: 'cash_flow', score: 0.68, cited: false },
  ];

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">RAG Inspector</h1>
        <p className="page-subtitle">Retrieved chunks with grounding attribution — cited vs uncited sources</p>
      </div>

      <div className="glass-card" style={{ marginBottom: 24 }}>
        <div style={{ marginBottom: 12 }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Query</span>
          <div style={{ fontSize: '1rem', fontWeight: 600, marginTop: 4 }}>{"What was AAPL's revenue in Q3 2024?"}</div>
        </div>
        <div style={{ padding: 16, background: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-sm)', fontSize: '0.9rem', lineHeight: 1.7 }}>
          {"Apple's total revenue for Q3 2024 (ending September 30, 2024) was "}
          <span className="chunk-text"><span className="citation">$89.50 billion [SOURCE_1]</span></span>
          {", representing growth from the previous quarter's "}
          <span className="chunk-text"><span className="citation">$85.78 billion [SOURCE_2]</span></span>
          {". Net income was $22.96B with an operating margin of approximately 33.1%."}
        </div>
      </div>

      <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 16 }}>Retrieved Chunks ({chunks.length})</h3>

      <div className="chunk-container">
        {chunks.map((chunk, i) => (
          <div key={chunk.id} className="chunk-card" style={{ borderLeft: chunk.cited ? '3px solid var(--accent-green)' : '3px solid var(--border-subtle)' }}>
            <div className="chunk-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="chunk-id">[SOURCE_{i + 1}]</span>
                <span className="chunk-id">{chunk.id}</span>
                {chunk.cited && <span style={{ fontSize: '0.65rem', background: 'rgba(16,185,129,0.15)', color: 'var(--accent-green)', padding: '2px 6px', borderRadius: 4 }}>CITED</span>}
                {!chunk.cited && <span style={{ fontSize: '0.65rem', background: 'rgba(255,255,255,0.05)', color: 'var(--text-muted)', padding: '2px 6px', borderRadius: 4 }}>NOT CITED</span>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="anomaly-type">{chunk.type}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>Score: {chunk.score}</span>
              </div>
            </div>
            <div className="code-block" style={{ marginTop: 8 }}>{chunk.text}</div>
            <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              📄 {chunk.docId} &middot; {chunk.ticker} &middot; Relevance: {(chunk.score * 100).toFixed(0)}%
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
