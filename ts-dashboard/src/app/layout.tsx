import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'FinAgentX — Operations Dashboard',
  description: 'Autonomous Financial Operations & Risk Intelligence System',
};

const navItems = [
  { href: '/', icon: '📊', label: 'Overview' },
  { href: '/traces', icon: '🔍', label: 'Agent Traces' },
  { href: '/anomalies', icon: '⚡', label: 'Anomaly Feed' },
  { href: '/rag', icon: '📚', label: 'RAG Inspector' },
  { href: '/evaluation', icon: '🧪', label: 'Evaluation' },
  { href: '/feedback', icon: '💬', label: 'Feedback' },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="app-layout">
          {/* Sidebar */}
          <nav className="sidebar">
            <div className="sidebar-logo">FinAgentX</div>
            <div className="sidebar-subtitle">Risk Intelligence System</div>

            <div className="nav-section-title">Navigation</div>
            {navItems.map((item) => (
              <a key={item.href} href={item.href} className="nav-link">
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </a>
            ))}

            <div style={{ flex: 1 }} />

            <div className="nav-section-title">System Status</div>
            <div style={{ padding: '0 12px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span className="status-dot online" /> AI Core
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span className="status-dot online" /> Gateway
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="status-dot online" /> Kafka
              </div>
            </div>
          </nav>

          {/* Main Content */}
          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
