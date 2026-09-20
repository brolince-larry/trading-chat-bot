# Forex AI Market Scanner

A deterministic forex market-analysis, strategy, risk-management, and
**paper-trading** engine (FastAPI backend + SvelteKit dashboard), with
live WebSocket updates for scanning, prices, and position tracking. This
is the Phase 1-6 "quantitative trading platform" core described in the
project spec, extended into Phase 9 (paper trading): **reliable market
data → deterministic analysis → tested strategies → risk engine → pair
scanner → live tracking**. It intentionally does not include an LLM/chat
layer or real broker execution yet — see [Roadmap](#roadmap).

**Backend: FastAPI (Python).** Kept from the original build — genuinely
lightweight (async ASGI, minimal overhead) for this workload, where the
bottleneck is market-data I/O, not language speed, and it already has 75
passing tests behind it.

**Frontend: SvelteKit + TypeScript + Tailwind CSS.** Chosen for being
"optimized and lightweight": Svelte compiles away the framework at build
time (no virtual DOM, no hydration overhead like React/Next.js), which
suits a dashboard that's mostly live-updating tables and numbers.

**No output from this system is a trade recommendation.** Every setup is
conditional ("a bullish continuation setup is developing if X confirms")
and carries an explicit invalidation condition. Position sizing and risk
checks are informational math, not investment advice. Nothing here should
be connected to a live trading account without independent review.

## Architecture

```
web/                    # SvelteKit dashboard
├── src/lib/api/         # Typed fetch client + TypeScript types mirroring app/schemas
├── src/lib/ws.ts        # Reconnecting WebSocket client helper
├── src/lib/components/  # Shared UI (TimeframeCard, ExposureChart, ...)
├── src/lib/format.ts    # Display formatting helpers
└── src/routes/          # 8 pages — see "What's implemented" below

app/
├── domain/            # Pure business logic, no framework/IO dependencies
│   ├── market/         # Candle/Price/SymbolSpec value objects + MarketDataProvider port
│   ├── analysis/        # Indicators, swing/trend/regime detection, TimeframeAnalysis
│   ├── strategies/       # Trend-pullback, breakout-retest, range-reversion strategies
│   ├── risk/            # Pip value, position sizing, exposure, risk-limit validation
│   ├── scanner/         # Setup quality scoring + multi-pair PairScanner orchestrator
│   └── trading/         # PaperPosition model + PaperTradingService (open/close/track/stats)
├── infrastructure/     # Adapters implementing domain ports
│   ├── market_data/     # SimulatedMarketDataProvider (dev/test), OandaMarketDataProvider
│   └── database/        # SQLAlchemy models, session, repositories (SQLite by default)
├── api/                # FastAPI routes (thin), WebSocket channels, background loop
├── schemas/            # Pydantic request/response DTOs
├── config.py           # Settings (env-driven)
└── main.py             # App entrypoint (starts the background loop on startup)
```

This follows the dependency-inversion rule from the spec: `app.domain`
defines `MarketDataProvider` as a `Protocol`; `app.infrastructure` provides
concrete implementations (simulated data for local dev/tests, a real OANDA
v20 REST adapter for production). Routes are thin and only translate
HTTP <-> domain calls; all decision logic (trend/regime classification,
strategy rules, position sizing, risk limits) lives in `app.domain` and is
covered by tests that don't touch the API or a database.

### Why deterministic code, not an LLM, makes the trading decisions

Strategies, indicators, and risk math are plain Python functions with
explicit numeric thresholds — not LLM calls. An LLM chat layer (a future
phase) would call these as tools and explain their output in natural
language, but it would never invent price levels, position sizes, or
risk-limit decisions itself.

## What's implemented

- **Market data**: `SimulatedMarketDataProvider` (deterministic, seeded
  synthetic OHLC — no credentials needed) and `OandaMarketDataProvider`
  (real OANDA v20 REST API; requires `OANDA_API_KEY`).
- **Indicators**: SMA, EMA, RSI, ATR, ADX/+DI/-DI, MACD, Bollinger Bands
  (Wilder's smoothing where applicable).
- **Structure**: fractal-based swing high/low detection, HH/HL vs LH/LL
  trend classification, support/resistance levels, trending/ranging/
  transitioning regime classification from ADX.
- **Strategies**: trend continuation/pullback, breakout-and-retest, and
  range mean-reversion — each returns a `TradeSetup` with an explicit
  status (`rejected` / `watching` / `confirmed` / `invalidated`), entry
  trigger, structure- and volatility-aware stop-loss, R-multiple take
  profits, and an invalidation condition. None of them ever claim
  certainty.
- **Risk engine**: correct pip-value math for any base/quote/account
  currency combination (not a hardcoded "$10/pip"), position sizing from
  account risk %, a currency-exposure aggregator (so three "different"
  long-USD-adjacent trades show up as one concentrated bet), and a
  configurable risk-limit validator (max risk/trade, max daily loss, max
  open positions, max spread, min risk/reward, max correlated exposure).
- **Scanner**: runs every strategy against every configured symbol across
  a higher (context) and entry timeframe, scores each actionable setup
  0-100 on objective factors (this is a **setup quality score, not a win
  probability**), and ranks candidates.
- **Paper trading**: open a simulated position from a confirmed candidate
  (sized via the real risk engine — never a hardcoded lot size); a
  background loop checks every open position against live prices every
  few seconds and auto-closes it on stop-loss or take-profit, exactly like
  a real execution/monitoring service would; a performance-stats endpoint
  computes win rate, expectancy (R), and profit factor from closed trades.
- **Live updates**: `/ws/scanner`, `/ws/prices`, and `/ws/positions`
  WebSocket channels, driven by an asyncio background loop (no Celery/Redis
  needed at this scale — see [Roadmap](#roadmap)).
- **Configurable risk limits**: max risk/trade, max daily loss, max open
  positions, max spread, min risk/reward, and max correlated exposure are
  persisted settings (`/api/v1/risk/limits`), editable from the dashboard.
- **Trading sessions & world clock**: real, DST-aware Sydney/Tokyo/London/
  New York open-closed status and a five-city world clock (New York, London,
  Lagos/WAT for "Africa time", Tokyo, Sydney), computed with `zoneinfo` — no
  external API needed — plus a flag for the London/New York, Tokyo/London,
  and Sydney/Tokyo high-liquidity overlap windows.
- **News feed port**: a `NewsProvider` port mirrors the market-data pattern.
  No real news/economic-calendar API is configured yet, so `/api/v1/news`
  and the dashboard's News panel honestly report "not connected" instead of
  ever fabricating headlines.
- **Manual trading UI**: a Trade panel on the Pair Analysis page to manually
  enter a trade (direction, entry, stop-loss, take-profit, sized by the real
  risk engine), adjust an open position's stop-loss/take-profit
  (`PATCH /api/v1/positions/{id}`), a normal "Exit Trade" button, and a
  emergency "🔥 Fire — Exit Now" button for closing immediately at market if
  the trade reverses.
- **API**: `/api/v1/market/*`, `/api/v1/analysis/{symbol}`,
  `/api/v1/scanner/run`, `/api/v1/risk/position-size`, `/api/v1/risk/limits`,
  `/api/v1/positions*`, `/api/v1/sessions`, `/api/v1/news`. See `/docs` for
  the live OpenAPI schema once running.
- **Dashboard (8 pages)**: Overview (stat tiles + currency-exposure chart),
  Scanner (live-updating, with an "Open" action per confirmed setup),
  Pair Analysis (live candlestick chart with EMA overlays and entry/stop/
  target price lines, the manual Trade panel, session clock, and news
  panel — plus a "best market to enter" callout from the scanner's top
  confirmed candidate), Positions (live P&L tracking), History (closed
  trades + performance stats), Live Prices, Position Size Calculator, and
  Risk Settings.

11 major/cross pairs are configured by default (`app/domain/market/symbols.py`).

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # SQLite + simulated provider by default — no external services needed
uvicorn app.main:app --reload
```

This also starts the background loop that drives the WebSocket channels
(re-scanning every 5s, re-pricing/checking positions every 2s — tune via
`BACKGROUND_SCAN_INTERVAL_SECONDS` / `BACKGROUND_PRICE_INTERVAL_SECONDS`).
Open `http://localhost:8000/docs` for interactive API docs, or:

```bash
curl -s -X POST http://localhost:8000/api/v1/scanner/run | jq
```

### Frontend dashboard

```bash
cd web
pnpm install
cp .env.example .env   # PUBLIC_API_BASE_URL, defaults to http://localhost:8000
pnpm run dev --open
```

Requires the backend running on `http://localhost:8000` (its CORS default
already allows the SvelteKit dev server at `http://localhost:5173`).

### With Docker Compose (backend + frontend + Postgres)

```bash
docker compose up --build
```

Runs the API on `:8000` (against Postgres — override `DATABASE_URL` to
keep SQLite instead) and the dashboard on `:3000`. The frontend's
production build uses `@sveltejs/adapter-node`, since `adapter-auto` can't
target a generic container.

### Tests

```bash
pytest              # backend: 119 tests
cd web && pnpm run check && pnpm run lint   # frontend: types + lint
```

The backend suite covers indicator math, structure/regime classification,
all three strategies' decision boundaries (reject/watch/confirm, both
directions), pip value and position sizing edge cases (including a
Decimal-serialization regression — see Known gotchas below), risk-limit
validation and persistence, paper-trading open/close/auto-close/stats
logic, the positions and risk-limits API routes against an isolated SQLite
DB per test, the scanner end to end against the simulated provider, and
the rest of the API layer.

### Known gotchas

- **Decimal scientific notation**: `Decimal` division/multiplication can
  legitimately produce a result with a positive exponent (e.g.
  `Decimal('0.0050') / Decimal('0.0001') == Decimal('5E+1')`), which
  `str()`-serializes as `"5E+1"` instead of `"50"` in API responses. Fixed
  once in `app/domain/risk/decimal_utils.to_plain`, applied at every
  Decimal result in the risk engine — if you add new Decimal arithmetic
  there, route it through `to_plain` too.

## Configuration

All settings are environment-driven (see `.env.example`); `app/config.py`
is the single place they're read. Notably:

- `DATABASE_URL` defaults to a local SQLite file (`sqlite:///./forex_ai.db`)
  — zero infrastructure to run. Point it at a `postgresql+psycopg://` URL
  (as `docker-compose.yml` does) for production; repositories are written
  to be dialect-agnostic.
- `MARKET_DATA_PROVIDER=simulated` (default) needs no credentials.
- `MARKET_DATA_PROVIDER=oanda` requires `OANDA_API_KEY`. The key is read
  only from settings/environment and is never logged, returned in an API
  response, or passed to an LLM.
- The database is optional for the analysis/scanner/risk-calculation
  endpoints, which are pure in-memory computation. `init_db()` degrades
  gracefully (logs a warning, doesn't crash the app) if the configured
  database isn't reachable at startup — positions/risk-limits persistence
  would be degraded, everything else keeps working.

## Security notes

- All API inputs are validated with Pydantic (bounded numeric ranges,
  symbol allowlists, currency-code format, request size limits on scans).
- Unhandled exceptions return a generic `500` with no internal detail;
  full tracebacks are only logged server-side.
- Money math uses `Decimal` throughout the risk engine — never `float` —
  to avoid rounding drift in position sizing.
- No secrets are hardcoded; broker credentials come from environment
  variables only.

## Roadmap (not yet built)

Following the phased plan in the project spec:

- **AI chat layer**: an LLM with function-calling access to
  `scan_all_pairs`, `get_pair_analysis`, `calculate_position_size`,
  `open_position`, etc., that explains structured output in natural
  language — never inventing numbers itself.
- **Economic calendar / news-risk integration**: currently the scanner's
  "session/news" scoring factor is a neutral placeholder score, clearly
  documented as such in `app/domain/scanner/scoring.py`, until a real
  calendar feed is wired in. The `NewsProvider` port (see above) is ready
  for a real adapter — swap `NoOpNewsProvider` for one backed by an actual
  news/calendar API and both the score and `/api/v1/news` light up.
- **Historical backtesting engine** with realistic spread/slippage
  modeling and drawdown/Sharpe metrics — paper trading (now built) tells
  you what's happening going forward; backtesting is still needed to
  validate a strategy against history before trusting it.
- **Demo broker execution** with manual approval, only after paper
  trading has been run long enough to trust the strategies — per the
  spec, never automated live execution as a first step.
- **Live candlestick charts** (TradingView Lightweight Charts,
  framework-agnostic) on the Pair Analysis and Live Prices pages.
- **Multi-instance scaling**: the current WebSocket broadcast manager and
  background loop are in-process, correct for a single API instance.
  Scaling to multiple instances would need the broadcast layer backed by
  Redis pub/sub and the background loop moved to a single leader (or a
  proper task queue like Celery/APScheduler-with-locking).
