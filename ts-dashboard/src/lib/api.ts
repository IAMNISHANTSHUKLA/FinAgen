/** FinAgentX — Gateway REST API Client */

import type { QueryRequest, QueryResponse, Alert, FeedbackEntry } from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  submitQuery: (req: QueryRequest) =>
    fetchAPI<QueryResponse>('/api/v1/query', { method: 'POST', body: JSON.stringify(req) }),

  getTrace: (sessionId: string) =>
    fetchAPI<QueryResponse>(`/api/v1/trace/${sessionId}`),

  getAlerts: () =>
    fetchAPI<{ alerts: Alert[] }>('/api/v1/alerts'),

  submitFeedback: (entry: FeedbackEntry) =>
    fetchAPI<{ status: string }>('/api/v1/feedback', { method: 'POST', body: JSON.stringify(entry) }),

  getHealth: () =>
    fetchAPI<{ status: string }>('/health'),
};
