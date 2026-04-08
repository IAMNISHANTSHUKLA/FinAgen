/** FinAgentX — Domain Type Contracts (matches protobuf schemas) */

export interface QueryRequest {
  session_id: string;
  query: string;
  user_id?: string;
  document_ids?: string[];
  intent?: string;
  metadata?: Record<string, string>;
}

export interface QueryResponse {
  session_id: string;
  answer: string;
  steps: TraceStep[];
  citations: Citation[];
  confidence: number;
  intent: string;
  total_latency_ms: number;
  tokens_used?: number;
  requires_approval?: boolean;
  risk_flags?: string[];
}

export interface TraceStep {
  step_id: string;
  step_number: number;
  tool_name: string;
  input_json: string;
  output_json: string;
  latency_ms: number;
  confidence: number;
  reasoning: string;
  risk_flags?: string[];
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  text: string;
  relevance_score: number;
  metadata: Record<string, string>;
  is_grounded: boolean;
}

export interface Alert {
  alert_id: string;
  ticker: string;
  alert_type: string;
  risk_score: number;
  description: string;
  recommended_action: string;
  timestamp: number;
}

export interface EvalResult {
  query: string;
  correctness: number;
  faithfulness: number;
  hallucination_detected: boolean;
  grounded_claims: string[];
  ungrounded_claims: string[];
}

export interface FeedbackEntry {
  session_id: string;
  user_id: string;
  feedback_type: 'thumbs_up' | 'thumbs_down' | 'correction';
  correction?: string;
  comment?: string;
}

export interface FeedbackStats {
  total_feedback: number;
  positive: number;
  negative: number;
  corrections: number;
  satisfaction_rate: number;
}
