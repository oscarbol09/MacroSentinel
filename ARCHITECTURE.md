# Architecture & System Design — MacroSentinel
 
MacroSentinel is an autonomous macroeconomic intelligence engine designed to continuously monitor central bank communications, track key financial indicators across multiple federal and institutional endpoints (FRED, U.S. Treasury, BLS, CFTC), assess monetary policy stance using structured LLM reasoning (FinCoT & Dialectical Debate), and publish executive briefs (*Macro Pulse*).

---

## 1. System Pipeline & Topology

```
┌─────────────────────────────────────────────────────────────┐
│                    APScheduler / CLI Engine                 │
└──────────────┬───────────────────────────────┬──────────────┘
               │                               │
               ▼                               ▼
    [ Multi-Source Extractors ]    [ Central Bank Extractor ]
    • FRED (14 Macro Series)       • FOMC Statements (RSS/Atom)
    • U.S. Treasury Fiscal Data    • ECB Press Releases
    • BLS API v2 (CPI / Payrolls)  • SSRF & Payload Size Guards
    • CFTC COT (Futures Net Pos)   • Content SHA-256 Hashing
               │                               │
               └───────────────┬───────────────┘
                               ▼ (Scatter-Gather Async)
               [ Circuit Breaker & Quarantine DLQ ]
               • 3-strike failure isolation per source
               • Dead Letter Queue in SQLite WAL
                               ▼
               [ Local SQLite Store (WAL Mode) ]
               • Deduplication of analyzed statements
               • Historical regime & tone time series
                               │
                               ▼
               [ LLM Reasoning Engine (Structured) ]
               • 4-Step Financial Chain-of-Thought (FinCoT)
               • Dialectical Debate (Hawk vs. Dove)
               • Investment Clock Regime Classification
               • Deterministic fallback heuristic when offline
                               │
                               ▼
               [ Chart Engine (Matplotlib Headless) ]
               • 10Y - 2Y Yield curve spread visualization
                               │
                               ▼
               [ Report Generator & Dispatchers ]
               ├── Markdown Brief (data/reports/)
               ├── Interactive Rich Terminal Dashboard
               ├── Telegram HTML Bot Alerts
               └── Responsive Email Digest (Resend API)
```

---

## 2. Core Architectural Decisions (ADRs)

### ADR-001: Puntos Básicos (bps) vs. Variación Porcentual Relativa
* **Context:** Computing standard percentage change $(\Delta / \text{prev} \times 100)$ on yield curve spreads (e.g., `T10Y2Y` going from $-0.18\%$ to $-0.12\%$) produces mathematically distorted values ($+33.3\%$) that misrepresent interest rate dynamics.
* **Decision:** Series with `unit == "Percent"` are calculated in **Basis Points (bps)** ($\Delta \times 100$), whereas non-rate indices (`CPIAUCSL`, `M2SL`) retain relative percentage changes.

### ADR-002: Local Persistence with SQLite WAL Mode
* **Context:** Ingestion workers running periodically must avoid re-running expensive LLM reasoning on already-processed statements and must track historical score trajectory.
* **Decision:** Embedded SQLite database located in `data/macrosentinel.db` with `journal_mode=WAL` and `synchronous=NORMAL`. Guarantees single-node zero-config reliability without requiring external database services.

### ADR-003: Deterministic Fallback Invariant
* **Context:** LLM API providers may experience rate limits, outages, or missing credentials during local development.
* **Decision:** `LLMReasoner` provides a rule-based quantitative fallback evaluator that calculates yield curve anomalies and labor market inflection rules deterministically, ensuring reports are always generated.

### ADR-004: Scatter-Gather Extraction with Circuit Breakers
* **Context:** A failure in an upstream governmental endpoint (e.g. CFTC or Treasury API maintenance) should never halt the entire macroeconomic analysis pipeline.
* **Decision:** Ingestion tasks run concurrently with `asyncio.gather(..., return_exceptions=True)`. Each source maintains an independent circuit breaker tripping after 3 consecutive failures.

### ADR-005: Dialectical Debate & Investment Clock Grounding
* **Context:** Monolithic LLM prompts often suffer from confirmation bias and bullish/complacent tone drift when summarizing central bank transcripts.
* **Decision:** The prompt explicitly instantiates an adversarial debate between an inflation-vigilant Hawkish persona and a growth/labor-vigilant Dovish persona, mapping the synthesized consensus into the 4 classic quadrants of the Investment Clock.

---

## 3. Storage Schema

### `processed_releases`
* `url` (TEXT, PRIMARY KEY): Remote feed entry permalink.
* `content_hash` (TEXT, INDEXED): SHA-256 digest of clean statement text.
* `institution` (TEXT): Central bank identifier (e.g. `Federal Reserve (FOMC)`).
* `title` (TEXT): Release title.
* `published_date` (TEXT): ISO or RFC-822 publication date.
* `processed_at` (TEXT): UTC ISO timestamp of analysis.

### `report_history`
* `report_id` (TEXT, PRIMARY KEY): Unique identifier (e.g. `MP-20260922-120000`).
* `generated_at` (TEXT, INDEXED): UTC ISO timestamp.
* `primary_regime` (TEXT): Macro regime classification.
* `tone_score` (REAL): Monetary policy tone in range `[-1.0, 1.0]`.
* `stance` (TEXT): Categorical stance (`Hawkish`, `Dovish`, `Neutral`).
* `confidence` (REAL): Assessment confidence level `[0.0, 1.0]`.
* `report_path` (TEXT): Local path to Markdown report.
* `raw_json` (TEXT): Full structured synthesis payload.

### `pipeline_quarantine`
* `id` (INTEGER, PRIMARY KEY AUTOINCREMENT): Failure log sequence ID.
* `source` (TEXT, INDEXED): Name of the data source (e.g. `Treasury`, `BLS`, `FRED`).
* `error_message` (TEXT): Summary of the exception or status code.
* `error_traceback` (TEXT): Full stack trace for debugging.
* `payload` (TEXT): Request payload or parameters when the failure occurred.
* `retry_count` (INTEGER): Number of retries executed prior to quarantine.
* `created_at` (TEXT): UTC ISO timestamp of isolation.
* `resolved_at` (TEXT): Timestamp when replayed or cleared.

