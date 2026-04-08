# FinAgentX — Autonomous Financial Operations & Risk Intelligence System

> **Product Requirement Document (PRD) + Technical Design Specification**

---

## 1. Executive Summary

**FinAgentX** is an agentic AI platform that continuously monitors financial data streams, performs autonomous anomaly detection, and delivers actionable risk intelligence — all with production-grade reliability, auditability, and compliance controls required by financial institutions.

### The Problem

Financial operations teams drown in data. A typical enterprise fund monitors 50+ tickers, ingests thousands of market events daily, and must process earnings reports, SEC filings, and real-time anomalies — all while maintaining regulatory compliance. Today this requires:

| Pain Point | Impact |
|---|---|
| **Manual anomaly triage** | 3-4 analysts spending 6+ hours/day scanning dashboards |
| **Disconnected data sources** | Revenue data in spreadsheets, market data in terminals, risk flags in emails |
| **Delayed risk detection** | Anomalies discovered hours or days after occurrence |
| **No audit trail** | "Who approved this trade?" has no verifiable answer |
| **LLM hallucination risk** | Generic AI tools fabricate financial data, creating compliance liability |

### The Solution

FinAgentX replaces manual financial analysis with an autonomous AI agent that:

1. **Ingests real market data** from Yahoo Finance (OHLCV, income statements, balance sheets, cash flows) across 15+ tickers including high-risk meme stocks
2. **Detects anomalies in real-time** via Kafka event streaming with 4 pluggable detection rules (volume spikes, price crashes, recurring changes, high-risk activity)
3. **Answers complex financial questions** using a RAG pipeline hardened against 15 documented failure modes — with provenance-tracked citations back to source documents
4. **Takes autonomous action** via tool-calling agents with guardrails (loop detection, timeout, human approval gates, max step limits)
5. **Maintains a tamper-proof audit trail** via SHA-256 hash-chained WORM storage on S3

### Business Impact (Projected)

| Metric | Before | After | Improvement |
|---|---|---|---|
| Anomaly detection latency | 4-8 hours | < 30 seconds | **960x faster** |
| Analyst hours on triage | 24 hrs/day (4 FTEs) | 4 hrs/day (1 FTE review) | **6x reduction** |
| Missed anomaly rate | ~18% | < 3% (with eval harness) | **6x fewer misses** |
| Audit readiness | Manual log compilation | Continuous hash-chained trail | **Always audit-ready** |
| Hallucination rate | Uncontrolled | < 5% (LLM-as-judge verified) | **Measurable & controlled** |

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TypeScript Dashboard (Next.js 14)                 │
│  Overview │ Agent Traces │ Anomaly Feed │ RAG Inspector │ Eval │ FB │
└────────────────────────────┬────────────────────────────────────────┘
                             │ REST + JWT RS256
┌────────────────────────────▼────────────────────────────────────────┐
│                    Go Event Gateway (Go 1.22)                       │
│  gRPC + REST │ Kafka Worker Pool (bounded) │ Circuit Breaker        │
│  JWT Auth (shared RS256) │ WORM Audit (S3 + SHA-256 chain)          │
│  Retry + Backoff │ DLQ routing │ Prometheus metrics                 │
└────────┬───────────────────┬────────────────────────────────────────┘
         │ gRPC/REST         │ Kafka
┌────────▼───────────────────▼────────────────────────────────────────┐
│                    Python AI Core (FastAPI + LangGraph)              │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────────────┐ │
│  │ Agent Layer   │  │ RAG Pipeline  │  │ Evaluation Engine        │ │
│  │              │  │ (15 fixes)    │  │                          │ │
│  │ • LangGraph  │  │ • Hybrid BM25 │  │ • LLM-as-Judge          │ │
│  │   Orchestr.  │  │   + Dense     │  │ • Correctness            │ │
│  │ • Tool Reg.  │  │ • Semantic    │  │ • Faithfulness           │ │
│  │ • Guardrails │  │   Chunking    │  │ • Hallucination          │ │
│  │ • Tool Sel.  │  │ • Reranking   │  │ • Precision@K            │ │
│  │ • Prompts    │  │ • Citations   │  │ • Synthetic Test Gen     │ │
│  └──────────────┘  └───────────────┘  └──────────────────────────┘ │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Infrastructure: Cerebras LLM │ Weaviate │ Redis │ Presidio  │   │
│  │ JWT RS256 │ Prometheus │ structlog │ PII Masking             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
         │              │            │             │
    Weaviate         Redis        Kafka         MinIO/S3
   (Vectors)       (State)     (Events)        (Audit)
```

### Service Contracts

| Service | Language | Port(s) | Protocol | Auth |
|---|---|---|---|---|
| **Python AI Core** | Python 3.12 | 8000 | REST | JWT RS256 on all `/api/*` routes |
| **Go Event Gateway** | Go 1.22 | 8080 (gRPC), 8443 (REST) | gRPC + REST | JWT interceptor (gRPC), JWT middleware (REST) |
| **TS Dashboard** | TypeScript / Next.js 14 | 3000 | HTTP | Bearer token passed to Gateway |
| **Cross-service** | — | — | Protobuf v3 | Shared RS256 public key in all 3 services |

---

## 3. Data Strategy: Real Yahoo Finance Data

**Zero synthetic data.** All financial data comes from `yfinance` — publicly verifiable against Yahoo Finance.

### Data Sources

| Source | API | What We Pull | Volume |
|---|---|---|---|
| `yfinance` OHLCV | `stock.history(period="2y")` | Open, High, Low, Close, Volume for 15 tickers | ~7,500 daily events |
| `yfinance` Financials | `stock.income_stmt`, `balance_sheet`, `cashflow` | 4 quarters × 3 statement types × 5 tickers | ~60 financial documents |
| Derived Anomaly Flags | Computed | Volume spikes (>3x avg), daily crashes (>10%), price deviations (>15%) | Pre-labeled ground truth |

### Tickers Monitored

| Category | Tickers | Purpose |
|---|---|---|
| **Blue Chip** | AAPL, MSFT, GOOGL, AMZN, META, NVDA | Stable baselines with earnings-driven anomalies |
| **Banking** | JPM, BAC, GS | Sector-specific financial health analysis |
| **High Risk** | GME, AMC, BBBY, COIN, MSTR | Meme stocks + crypto-correlated for anomaly richness |

### Data Pipeline

```
Yahoo Finance → market_data_loader.py → transactions.jsonl (Kafka)
                                      → financial_statements.jsonl (Weaviate RAG)
                                      → test_queries.json (Evaluation)
```

---

## 4. Security Architecture

### Authentication: Shared RS256 JWT Across All Services

```
               ┌───────────────┐
               │ JWT Issuer    │
               │ (RS256 keys)  │
               └───────┬───────┘
                       │ Public Key
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
  Python AI Core  Go Gateway   TS Dashboard
  (PyJWT)         (golang-jwt) (fetch header)
```

- **Algorithm:** RS256 (asymmetric — private key signs, public key verifies)
- **Claims:** `sub` (user ID), `roles` (analyst/engineer/admin), `allowed_tickers`, `max_risk_level`
- **Enforcement:**
  - Python: `Depends(get_current_user)` on every `/api/*` route
  - Go gRPC: Unary interceptor validates all non-health RPCs
  - Go REST: `jwtRESTMiddleware()` wraps all `/api/*` handlers
  - Dev mode: When `JWT_PUBLIC_KEY` env var is empty, auth degrades gracefully with warning

### Authorization: Role-Based Access Control (RBAC)

| Tool/Action | `analyst` | `engineer` | `admin` |
|---|---|---|---|
| `analyze_spend` | ✅ | ✅ | ✅ |
| `detect_anomaly` | ✅ | ✅ | ✅ |
| `recommend_action` | ❌ | ✅ | ✅ |
| `generate_report` | ✅ | ✅ | ✅ |
| Document Ingestion | ❌ | ✅ | ✅ |
| Run Evaluation | ❌ | ✅ | ✅ |
| Submit Feedback | ✅ | ✅ | ✅ |

### Data Protection

| Control | Implementation |
|---|---|
| **PII Masking** | Microsoft Presidio — reversible tokenization with UUID tokens |
| **PII Storage** | Reverse maps stored in Redis with 1hr TTL, auto-expired |
| **Audit Trail** | S3 Object Lock (WORM) with SHA-256 hash chain |
| **Chain Integrity** | Each entry hashes over `(data + previous_hash)` — tamper-evident |
| **API Hardening** | HSTS, X-Frame-Options: DENY, Content-Type-Options: nosniff, request size limits (1MB), restricted CORS |

---

## 5. RAG Pipeline — 15 Failure Fixes

Every production RAG system encounters these failure modes. FinAgentX addresses all 15:

| # | Failure Mode | Fix | Module |
|---|---|---|---|
| 1 | **Retrieval Miss** | Hybrid BM25 + dense search (α=0.75, RRF) | `retriever.py` |
| 2 | **Low Recall** | Multi-query retrieval + parent-child chunking | `retriever.py`, `chunker.py` |
| 3 | **Bad Chunking** | Semantic chunking with 20% overlap + section preservation | `chunker.py` |
| 4 | **Embedding Drift** | Version tracking + re-embed detection | `embedding_manager.py` |
| 5 | **Context Overflow** | Cross-encoder reranking + context compression + token budgeting | `reranker.py` |
| 6 | **Hallucination** | Grounded prompting + citation verification chain | `citations.py`, `prompts.py` |
| 7 | **No Provenance** | Citation-aware prompting with `[SOURCE_N]` markers | `citations.py` |
| 8 | **Stale Data** | Exponential freshness scoring + incremental indexing | `indexer.py` |
| 9 | **Latency Explosion** | Redis embedding + response cache with TTL | `cache.py` |
| 10 | **Cost Explosion** | Cascaded inference (cheap 8B → expensive 70B on low confidence) | `cascade.py` |
| 11 | **Wrong Intent** | LLM-based query classification + routing | `query_engine.py` |
| 12 | **Low Precision** | Two-stage retrieval: fast hybrid → neural cross-encoder rerank | `reranker.py` |
| 13 | **Data Leakage** | Retrieval-time authorization (ACLs on chunks) | `authorization.py` |
| 14 | **No Eval Pipeline** | LLM-as-judge + precision@k + recall@k + synthetic test gen | `judge.py`, `metrics.py` |
| 15 | **No Feedback Loop** | Active learning: flag low-confidence queries for human review | `feedback.py` |

---

## 6. Agentic System — 4 Safeguards

### Tool Calling Architecture

```
User Query → Intent Classifier → Tool Selector
                                      │
                ┌─────────────────────┼─────────────────────┐
                ▼                     ▼                     ▼
         analyze_spend        detect_anomaly        generate_report
         (Pydantic I/O)       (Pydantic I/O)        (Pydantic I/O)
                │                     │                     │
                └─────────────────────┼─────────────────────┘
                                      ▼
                              LangGraph Orchestrator
                              (Plan → Execute → Reason → Answer)
                                      │
                              Redis Checkpointer
                              (crash-recoverable)
```

### Safeguards

| # | Safeguard | Implementation |
|---|---|---|
| A1 | **Tool Mis-Selection** | LLM-based classifier selects tools by semantic matching, not string matching |
| A2 | **Infinite Loops** | Loop detection (same tool + same input ≥ 3x), max 10 steps, 60s timeout |
| A3 | **Unauthorized Actions** | RBAC + human approval gates for high-risk tools when confidence < 0.7 |
| A4 | **Poor Planning** | Structured planning prompts with JSON plan output before execution |

---

## 7. Observability

### Prometheus Metrics (15+ metrics)

| Metric | Type | Labels |
|---|---|---|
| `finagentx_query_duration_seconds` | Histogram | intent, status |
| `finagentx_tokens_total` | Counter | model, type |
| `finagentx_tool_calls_total` | Counter | tool_name, status |
| `finagentx_hallucinations_total` | Counter | — |
| `finagentx_cache_hits_total` | Counter | cache_type |
| `finagentx_retrieval_precision_at_k` | Gauge | k |
| `finagentx_errors_total` | Counter | service, error_type |
| `finagentx_guardrail_triggers_total` | Counter | guardrail_type |

### Grafana Dashboard (10 panels)

Pre-built `infra/grafana/dashboards/finagent.json` with: Query latency (p50/p95/p99), Token usage rate, Error rate by service, Hallucination rate gauge, Cache hit rate gauge, Kafka consumer lag, Anomaly alerts rate, Circuit breaker state, Retrieval precision@K, Tool call distribution pie chart.

### Structured Logging

- **Format:** JSON (structlog) with correlation IDs across request lifecycle
- **Tracing:** Every request gets a `correlation_id` propagated through Python → Go → downstream

---

## 8. Infrastructure

### Docker Compose Stack

| Service | Image | Purpose |
|---|---|---|
| Kafka + Zookeeper | `confluentinc/cp-kafka:7.6.0` | Event streaming (3 topics + DLQ) |
| Weaviate | `semitechnologies/weaviate:1.24.10` | Vector DB (hybrid search, reranker) |
| Redis | `redis:7.2-alpine` | State, cache, PII token maps |
| MinIO | `minio/minio:latest` | S3-compatible WORM audit storage |
| Prometheus | `prom/prometheus:v2.51.0` | Metrics collection |
| Grafana | `grafana/grafana:10.4.0` | Dashboards |

### Kubernetes Manifests

8 production-ready manifests with:
- **Liveness + Readiness probes** on all services
- **Resource limits** (CPU/memory requests and limits)
- **StatefulSets** for stateful services (Kafka, Weaviate, Redis)
- **LoadBalancer** type services for Gateway and Dashboard
- **Secrets** management via `finagentx-secrets`

---

## 9. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **LLM Provider** | Cerebras API (LLaMA 3.1-70B / 8B) | No OpenAI dependency, open-source models |
| **Agent Framework** | LangGraph + Redis checkpointing | Crash-recoverable stateful workflows |
| **Vector Database** | Weaviate | Native hybrid search (BM25 + dense), reranker module |
| **Streaming** | Apache Kafka | Production event bus with DLQ, 3-topic setup |
| **API Gateway** | Go (gRPC + REST) | Sub-millisecond routing, circuit breakers, 10-worker bounded pool |
| **Dashboard** | Next.js 14 + TypeScript | Server components, glassmorphism UI |
| **Auth** | RS256 JWT (shared across 3 services) | Asymmetric — no shared secret risk |
| **PII Protection** | Microsoft Presidio | Reversible tokenization for financial entities |
| **Observability** | Prometheus + Grafana + structlog | 15+ custom metrics, pre-built dashboard |
| **Data Source** | Yahoo Finance (yfinance) | Real, verifiable market data — zero synthetic |
| **Containerization** | Docker + Kubernetes | Multi-stage builds, health checks, StatefulSets |

---

## 10. Clean Architecture (SOLID)

| Principle | Application |
|---|---|
| **Single Responsibility** | Each module owns exactly one failure fix (e.g., `chunker.py` = Fix #3) |
| **Open/Closed** | Tool registry and anomaly rules are extensible without modifying orchestrator |
| **Liskov Substitution** | `BaseChatModel` adapter — Cerebras, Ollama, or any LLM swaps in transparently |
| **Interface Segregation** | 9 narrow ABCs: `LLMClient`, `VectorStore`, `Reranker`, `Cache`, `PIIMasker`, `Authorizer`, `FeedbackStore`, `AuditLogger`, `Embedder` |
| **Dependency Inversion** | Orchestrator depends on `LLMClient` ABC, not `CerebrasAdapter` directly |

### Layer Separation

```
Domain Layer          → Schemas, Interfaces, Exceptions (zero external deps)
Application Layer     → RAG Pipeline, Agent Orchestrator, Evaluation Engine
Infrastructure Layer  → Cerebras, Weaviate, Redis, Presidio, Prometheus
Presentation Layer    → FastAPI routes, gRPC handlers, Next.js UI
```

---

## 11. Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/your-org/finagentx.git
cd finagentx
cp .env.example .env
# Set CEREBRAS_API_KEY in .env

# 2. Start infrastructure
cd infra && docker-compose up -d

# 3. Seed REAL market data from Yahoo Finance
cd infra/data && pip install yfinance && python market_data_loader.py

# 4. Start Python AI Core
cd python-ai-core && pip install -r requirements.txt && uvicorn main:app --reload --port 8000

# 5. Start Go Gateway
cd go-gateway && go mod tidy && go run ./cmd/server/

# 6. Start Dashboard
cd ts-dashboard && npm install && npm run dev

# 7. Open Dashboard → http://localhost:3000
```

---

## 12. File Inventory (80 files)

| Directory | Files | Purpose |
|---|---|---|
| `infra/` | 14 | Protobuf, Docker Compose, K8s manifests, Prometheus, Grafana, data seeder |
| `python-ai-core/domain/` | 3 | Pure Python schemas, interfaces, exceptions |
| `python-ai-core/infrastructure/` | 8 | Cerebras adapter, Weaviate, Redis, Presidio, JWT, Prometheus, structlog |
| `python-ai-core/application/rag/` | 13 | Query engine, chunker, retriever, reranker, citations, indexer, cache, cascade, auth, feedback, parser, ingestor, embedding manager |
| `python-ai-core/application/agent/` | 7 | Tool registry, selector, tools (4), guardrails, prompts, graph state, orchestrator |
| `python-ai-core/application/eval/` | 3 | LLM judge, metrics, synthetic test generator |
| `python-ai-core/` | 4 | main.py, config, requirements.txt, Dockerfile |
| `go-gateway/` | 12 | Domain models, rules, anomaly detector, Kafka consumer, audit logger, circuit breaker, retry, JWT, main, Dockerfile |
| `ts-dashboard/` | 13 | 6 pages, layout, CSS design system, types, API client, configs, Dockerfile |

---

*FinAgentX — Where autonomous intelligence meets financial-grade compliance.*
#   F i n A g e n  
 