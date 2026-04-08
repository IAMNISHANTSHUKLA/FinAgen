"""
FinAgentX — Real Market Data Loader (yfinance)

Pulls REAL financial data from Yahoo Finance for:
- Transaction-like events for Kafka streaming
- Financial statements for RAG document ingestion
- Real anomalies (volume spikes, price crashes, earnings surprises)

No Faker dependency. All data is verifiable against public markets.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import yfinance as yf

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "NVDA", "META", "JPM", "BAC", "GS"]
HIGH_RISK_TICKERS = ["GME", "AMC", "BBBY", "COIN", "MSTR"]
LOOKBACK_DAYS = 365 * 2  # 2 years of data

OUTPUT_DIR = Path(__file__).parent.parent / "sample-data"


def load_price_data(tickers: list[str], period: str = "2y") -> list[dict]:
    """Load OHLCV data and convert to transaction-like events."""
    events = []

    for ticker in tickers:
        print(f"  Fetching {ticker}...")
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            print(f"  WARNING: No data for {ticker}, skipping.")
            continue

        # Compute rolling stats for anomaly detection
        hist["vol_30d_avg"] = hist["Volume"].rolling(window=30).mean()
        hist["price_30d_avg"] = hist["Close"].rolling(window=30).mean()
        hist["daily_return"] = hist["Close"].pct_change()

        info = stock.info
        sector = info.get("sector", "Unknown")
        industry = info.get("industry", "Unknown")
        is_high_risk = ticker in HIGH_RISK_TICKERS

        for date, row in hist.iterrows():
            if row.get("vol_30d_avg") and row["vol_30d_avg"] > 0:
                volume_ratio = row["Volume"] / row["vol_30d_avg"]
            else:
                volume_ratio = 1.0

            if row.get("price_30d_avg") and row["price_30d_avg"] > 0:
                price_deviation = (row["Close"] - row["price_30d_avg"]) / row["price_30d_avg"]
            else:
                price_deviation = 0.0

            event = {
                "event_id": f"{ticker}-{date.strftime('%Y%m%d')}",
                "ticker": ticker,
                "date": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
                "daily_return_pct": round(float(row.get("daily_return", 0) * 100), 4),
                "volume_vs_30d_avg": round(float(volume_ratio), 2),
                "price_deviation_30d_pct": round(float(price_deviation * 100), 2),
                "sector": sector,
                "industry": industry,
                "high_risk": is_high_risk,
                # Pre-flag anomalies for evaluation ground truth
                "anomaly_flags": _detect_anomalies(
                    volume_ratio, price_deviation, row.get("daily_return", 0), is_high_risk
                ),
            }
            events.append(event)

    return events


def _detect_anomalies(
    volume_ratio: float,
    price_deviation: float,
    daily_return: float,
    is_high_risk: bool,
) -> list[str]:
    """Pre-label anomalies as ground truth for evaluation."""
    flags = []

    # Rule 1: Volume spike > 3x 30-day average
    if volume_ratio > 3.0:
        flags.append(f"VOLUME_SPIKE_{volume_ratio:.1f}x")

    # Rule 2: Price deviation > 15% from 30-day average
    if abs(price_deviation) > 0.15:
        direction = "UP" if price_deviation > 0 else "DOWN"
        flags.append(f"PRICE_DEVIATION_{direction}_{abs(price_deviation)*100:.1f}pct")

    # Rule 3: Single-day crash/surge > 10%
    if abs(daily_return) > 0.10:
        direction = "SURGE" if daily_return > 0 else "CRASH"
        flags.append(f"DAILY_{direction}_{abs(daily_return)*100:.1f}pct")

    # Rule 4: High-risk ticker activity
    if is_high_risk and (volume_ratio > 2.0 or abs(daily_return) > 0.05):
        flags.append("HIGH_RISK_ACTIVITY")

    return flags


def load_financial_statements(tickers: list[str]) -> list[dict]:
    """Load real financial statements for RAG ingestion."""
    documents = []

    for ticker in tickers[:5]:  # Top 5 for statements
        print(f"  Fetching financials for {ticker}...")
        stock = yf.Ticker(ticker)

        # Income Statement
        income = stock.income_stmt
        if income is not None and not income.empty:
            for col in income.columns[:4]:  # Last 4 quarters
                doc = {
                    "document_id": f"{ticker}-income-{col.strftime('%Y%m%d')}",
                    "ticker": ticker,
                    "document_type": "income_statement",
                    "period": col.strftime("%Y-%m-%d"),
                    "data": {},
                }
                for idx in income.index:
                    val = income.loc[idx, col]
                    if val is not None and str(val) != "nan":
                        doc["data"][str(idx)] = float(val)
                if doc["data"]:
                    # Generate human-readable text for RAG
                    doc["text"] = _format_statement(ticker, "Income Statement", col, doc["data"])
                    documents.append(doc)

        # Balance Sheet
        balance = stock.balance_sheet
        if balance is not None and not balance.empty:
            for col in balance.columns[:4]:
                doc = {
                    "document_id": f"{ticker}-balance-{col.strftime('%Y%m%d')}",
                    "ticker": ticker,
                    "document_type": "balance_sheet",
                    "period": col.strftime("%Y-%m-%d"),
                    "data": {},
                }
                for idx in balance.index:
                    val = balance.loc[idx, col]
                    if val is not None and str(val) != "nan":
                        doc["data"][str(idx)] = float(val)
                if doc["data"]:
                    doc["text"] = _format_statement(ticker, "Balance Sheet", col, doc["data"])
                    documents.append(doc)

        # Cash Flow
        cashflow = stock.cashflow
        if cashflow is not None and not cashflow.empty:
            for col in cashflow.columns[:4]:
                doc = {
                    "document_id": f"{ticker}-cashflow-{col.strftime('%Y%m%d')}",
                    "ticker": ticker,
                    "document_type": "cash_flow",
                    "period": col.strftime("%Y-%m-%d"),
                    "data": {},
                }
                for idx in cashflow.index:
                    val = cashflow.loc[idx, col]
                    if val is not None and str(val) != "nan":
                        doc["data"][str(idx)] = float(val)
                if doc["data"]:
                    doc["text"] = _format_statement(ticker, "Cash Flow Statement", col, doc["data"])
                    documents.append(doc)

    return documents


def _format_statement(ticker: str, stmt_type: str, period, data: dict) -> str:
    """Convert financial data to human-readable text for RAG."""
    period_str = period.strftime("%Y-%m-%d") if hasattr(period, "strftime") else str(period)
    lines = [f"{ticker} {stmt_type} for period ending {period_str}:", ""]

    for key, value in data.items():
        if abs(value) >= 1_000_000_000:
            formatted = f"${value / 1_000_000_000:.2f}B"
        elif abs(value) >= 1_000_000:
            formatted = f"${value / 1_000_000:.2f}M"
        elif abs(value) >= 1_000:
            formatted = f"${value / 1_000:.2f}K"
        else:
            formatted = f"${value:.2f}"

        lines.append(f"  {key}: {formatted}")

    return "\n".join(lines)


def generate_test_queries(tickers: list[str]) -> list[dict]:
    """Generate evaluation queries with verifiable expected answers."""
    queries = [
        {
            "query": f"What was {tickers[0]}'s total revenue in the most recent fiscal year?",
            "intent": "spend_analysis",
            "expected_tickers": [tickers[0]],
            "verification": "Check against income statement data",
        },
        {
            "query": f"Compare {tickers[0]} and {tickers[1]} net income over the last 4 quarters.",
            "intent": "comparison",
            "expected_tickers": [tickers[0], tickers[1]],
            "verification": "Cross-reference income statements",
        },
        {
            "query": f"Were there any volume anomalies in {tickers[3]} stock in the past 6 months?",
            "intent": "anomaly",
            "expected_tickers": [tickers[3]],
            "verification": "Check anomaly_flags in event data",
        },
        {
            "query": f"What is {tickers[0]}'s current debt-to-equity ratio?",
            "intent": "spend_analysis",
            "expected_tickers": [tickers[0]],
            "verification": "Calculate from balance sheet: total_debt / total_equity",
        },
        {
            "query": f"Analyze {tickers[2]}'s cash flow trend over the last year.",
            "intent": "report",
            "expected_tickers": [tickers[2]],
            "verification": "Check cash flow statements across quarters",
        },
        {
            "query": "Which stocks had the highest price volatility in the past 30 days?",
            "intent": "anomaly",
            "expected_tickers": tickers,
            "verification": "Compare daily_return_pct standard deviations",
        },
        {
            "query": f"Is {HIGH_RISK_TICKERS[0]} showing signs of unusual trading activity?",
            "intent": "anomaly",
            "expected_tickers": [HIGH_RISK_TICKERS[0]],
            "verification": "Check HIGH_RISK_ACTIVITY flags",
        },
        {
            "query": f"Generate a risk report for {tickers[7]} (banking sector).",
            "intent": "report",
            "expected_tickers": [tickers[7]],
            "verification": "Should include sector context and financial health metrics",
        },
        {
            "query": f"What percentage of {tickers[0]}'s revenue comes from services vs products?",
            "intent": "spend_analysis",
            "expected_tickers": [tickers[0]],
            "verification": "Check income statement breakdown",
        },
        {
            "query": f"Recommend portfolio actions based on {tickers[3]}'s recent price crash.",
            "intent": "report",
            "expected_tickers": [tickers[3]],
            "verification": "Should reference actual price data and provide grounded recommendation",
        },
        {
            "query": f"How does {tickers[5]}'s operating margin compare to industry average?",
            "intent": "comparison",
            "expected_tickers": [tickers[5]],
            "verification": "Calculate from income statement: operating_income / revenue",
        },
        {
            "query": "List all detected anomalies across all monitored tickers in the last quarter.",
            "intent": "anomaly",
            "expected_tickers": tickers + HIGH_RISK_TICKERS,
            "verification": "Aggregate anomaly_flags from all events",
        },
        {
            "query": f"What is {tickers[4]}'s free cash flow and how has it trended?",
            "intent": "spend_analysis",
            "expected_tickers": [tickers[4]],
            "verification": "Check cash flow statement: operating_cash_flow - capex",
        },
        {
            "query": f"Assess the financial health of {tickers[8]} as a banking institution.",
            "intent": "report",
            "expected_tickers": [tickers[8]],
            "verification": "Should include capital ratios, loan quality, revenue mix",
        },
        {
            "query": "Which high-risk tickers triggered the most anomaly alerts this year?",
            "intent": "anomaly",
            "expected_tickers": HIGH_RISK_TICKERS,
            "verification": "Count anomaly_flags per high-risk ticker",
        },
        {
            "query": f"Explain {tickers[6]}'s recent earnings surprise and its market impact.",
            "intent": "report",
            "expected_tickers": [tickers[6]],
            "verification": "Cross-reference earnings date with price/volume changes",
        },
        {
            "query": f"Calculate {tickers[0]}'s return on equity (ROE) for the latest quarter.",
            "intent": "spend_analysis",
            "expected_tickers": [tickers[0]],
            "verification": "ROE = net_income / shareholders_equity from statements",
        },
        {
            "query": "Identify any recurring patterns in volume spikes across tech stocks.",
            "intent": "anomaly",
            "expected_tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "META"],
            "verification": "Analyze VOLUME_SPIKE flags for temporal clustering",
        },
        {
            "query": f"Provide a comprehensive financial summary for {tickers[9]}.",
            "intent": "report",
            "expected_tickers": [tickers[9]],
            "verification": "Should cover income, balance sheet, cash flow, and market data",
        },
        {
            "query": "What is the current market sentiment based on recent price action across all monitored stocks?",
            "intent": "report",
            "expected_tickers": tickers,
            "verification": "Aggregate daily returns and anomaly flags for sentiment inference",
        },
    ]

    return queries


def main():
    """Main data loading pipeline."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_tickers = TICKERS + HIGH_RISK_TICKERS

    # 1. Load price/volume data as transaction events
    print("\n[1/3] Loading price data...")
    events = load_price_data(all_tickers)
    events_path = OUTPUT_DIR / "transactions.jsonl"
    with open(events_path, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    # Count anomalies
    anomaly_count = sum(1 for e in events if e["anomaly_flags"])
    print(f"  → {len(events)} events, {anomaly_count} with anomaly flags")

    # 2. Load financial statements for RAG
    print("\n[2/3] Loading financial statements...")
    documents = load_financial_statements(TICKERS)
    docs_path = OUTPUT_DIR / "financial_statements.jsonl"
    with open(docs_path, "w") as f:
        for doc in documents:
            f.write(json.dumps(doc) + "\n")
    print(f"  → {len(documents)} financial statement documents")

    # 3. Generate test queries
    print("\n[3/3] Generating test queries...")
    queries = generate_test_queries(TICKERS)
    queries_path = OUTPUT_DIR / "test_queries.json"
    with open(queries_path, "w") as f:
        json.dump(queries, f, indent=2)
    print(f"  → {len(queries)} evaluation queries")

    # Summary
    print(f"\n{'='*60}")
    print(f"Data seeding complete!")
    print(f"  Events:     {events_path}")
    print(f"  Statements: {docs_path}")
    print(f"  Queries:    {queries_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
