# Intel-AI — Pre-Event Anomaly Detection

> Detects "Pre-Event Anomalies" by monitoring the velocity and semantic shift of low-volume human behavior across search, social, and alternative data streams.

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env          # Edit with your credentials

# 2. Start everything (Postgres + API + Ingestion + Prometheus + Grafana)
docker-compose up -d

# 3. Run database migrations
docker-compose exec api alembic upgrade head

# 4. Open the dashboard
cd dashboard && npm install && npm run dev
# → http://localhost:3001
```

Default login: `admin` / `admin`

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DASHBOARD (Next.js 14)                       │
│  Alert Inbox │ Detail+Evidence │ Dashboard │ Sources │ Watchlist     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────────────┐
│                      FastAPI  (28+ endpoints)                       │
│  /api/alerts  /api/dashboard  /api/evidence  /api/feedback          │
│  /api/sources /api/watchlist  /api/detection  /api/auth             │
│  JWT Auth │ CORS │ Prometheus Metrics │ Structured Logging          │
└──────┬───────────────┬──────────────────────────────────────────────┘
       │               │
┌──────▼──────┐ ┌──────▼──────────────────────────────────────────────┐
│  Ingestion  │ │              Detection Pipeline                     │
│  Scheduler  │ │  Aggregator → STL + IForest + CUSUM → Ensemble     │
│             │ │  → Evidence Builder → Alert → Analog Match          │
│  4 Sources: │ │  → WebSocket Broadcast                              │
│  • G.Trends │ │                                                     │
│  • Wikipedia│ │  Semantic: SBERT Embedder → HDBSCAN → Drift        │
│  • Reddit   │ │  RL: Thompson Sampling weight tuning                │
│  • GDELT    │ │  Backtest: Historical replay engine                 │
└──────┬──────┘ └──────┬──────────────────────────────────────────────┘
       │               │
┌──────▼───────────────▼──────────────────────────────────────────────┐
│               PostgreSQL 16 (4 schemas)                             │
│  ingestion.* │ signal.* │ alert.* │ backtest.*   (15 tables)       │
└─────────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript, TailwindCSS, Recharts |
| API | FastAPI, Uvicorn, Pydantic 2.x, PyJWT |
| Database | PostgreSQL 16, SQLAlchemy 2.x async, Alembic |
| Detection | STL decomposition, Isolation Forest, CUSUM, SBERT, HDBSCAN |
| Ingestion | pytrends, aiohttp, asyncpraw, GDELT DOC API |
| Monitoring | Prometheus, Grafana, structured JSON logging |
| Deployment | Docker, docker-compose |

## Project Structure

```
src/vanguard_signal/
├── api/            # FastAPI app, routes, auth, WebSocket
├── ingestion/      # Scheduler, connectors (4 sources), storage
├── detection/      # STL, IForest, CUSUM, ensemble, pipeline
├── semantic/       # SBERT embedder, HDBSCAN clusterer, drift
├── backtest/       # Historical replay engine
├── schema/         # SQLAlchemy models (15 tables), enums, validators
├── config.py       # Environment-based configuration
└── logging_config.py

dashboard/src/
├── app/            # Next.js pages (App Router)
├── components/     # Shared React components
└── lib/            # API client, WebSocket hook, utilities

tests/              # pytest + pytest-asyncio test suite
alembic/            # Database migration scripts
deploy/             # Prometheus config
```

## Environment Variables

See [.env.example](.env.example) for the complete list. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `VS_ENV` | development | Environment mode |
| `VS_DB_HOST` | localhost | PostgreSQL host |
| `VS_JWT_SECRET` | (dev default) | JWT signing secret — **change in production** |
| `VS_SEMANTIC` | false | Enable SBERT semantic engine |
| `VS_RL_FEEDBACK` | false | Enable RL weight tuning |
| `VS_BACKTEST` | false | Enable backtesting engine |

## API Documentation

With the API running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

```bash
# Install Python deps
pip install -e ".[dev]"

# Run tests
make test

# Lint
make lint

# Start just the API (without Docker)
uvicorn vanguard_signal.api.app:app --reload --port 8000

# Start ingestion worker
python -m vanguard_signal.ingestion
```

## Alert Rules Guide

Alert Rules let you create custom conditions that automatically generate alerts based on trend data. Instead of waiting for the anomaly detection system to find patterns, you can define specific rules that trigger alerts when certain thresholds are met.

### What Are Alert Rules?

Alert Rules are like "if-then" statements for your trend data:
- **IF** a keyword's interest score goes above 80 in the US
- **THEN** create a high-priority alert

### How Alert Rules Work

1. **Rule Definition**: You create a rule with conditions (what to watch for)
2. **Monitoring**: The system continuously checks trend data against your rules
3. **Triggering**: When conditions are met, a trigger record is created
4. **Alert Creation**: If cooldowns allow, an alert is generated
5. **Notification**: You get notified via email/desktop based on rule settings

### Creating Your First Alert Rule

#### Basic Rule Fields

| Field | What it does | Example |
|-------|-------------|---------|
| **Name** | Friendly name for the rule | "Bank Run Detector" |
| **Description** | What this rule detects | "Alerts when banking terms spike" |
| **Condition Type** | What to measure | `interest_spike`, `velocity_threshold`, `rank_change` |
| **Threshold Value** | The trigger number | `75.0` (75% interest score) |
| **Comparison Operator** | How to compare | `>`, `>=`, `<`, `<=`, `==` |
| **Severity** | Alert importance | `low`, `medium`, `high`, `critical` |

#### Condition Types Explained

| Condition Type | What it measures | Use case |
|----------------|------------------|----------|
| `interest_spike` | Raw interest score (0-100) | "Alert when 'bitcoin' > 80" |
| `velocity_threshold` | Rate of change | "Alert when interest is rising fast" |
| `rank_change` | Position improvement | "Alert when term jumps in rankings" |
| `correlation` | Relationship between terms | "Alert when related terms move together" |

#### Targeting Specific Content

| Field | What it does | Example |
|-------|-------------|---------|
| **Target Keywords** | Specific terms to watch | `["bank run", "deposit flight"]` |
| **Target Categories** | Content categories | `["finance", "economics"]` |
| **Geo Scope** | Countries/regions | `["US", "GB", "DE"]` |

*Leave empty to monitor everything*

#### Notification Settings

| Setting | What it does |
|---------|-------------|
| **Notify Email** | Send email alerts |
| **Notify Desktop** | Show desktop notifications |
| **Email Recipients** | Who gets the emails |
| **Cooldown Minutes** | Wait time between alerts for same entity |

### Example Rules

#### 1. Banking Crisis Detector
```
Name: Banking Crisis Alert
Condition: interest_spike > 70
Target Keywords: ["bank run", "deposit insurance", "bank failure"]
Geo Scope: ["US"]
Severity: critical
Cooldown: 120 minutes
Notifications: Email + Desktop
```

#### 2. Social Media Trend Watcher
```
Name: Viral Content Alert
Condition: velocity_threshold > 50
Target Categories: ["social", "entertainment"]
Severity: medium
Cooldown: 30 minutes
Notifications: Desktop only
```

#### 3. Regional Interest Monitor
```
Name: Local Event Detector
Condition: rank_change >= 20
Geo Scope: ["US-CA", "US-NY", "US-TX"]
Severity: low
Cooldown: 60 minutes
Notifications: Email only
```

### Managing Alert Rules

#### Viewing Rules
- Go to the Alert Rules section in the dashboard
- See all active rules and their trigger history
- Check which rules are enabled/disabled

#### Editing Rules
- Click on any rule to modify its settings
- Change thresholds, keywords, or notification settings
- Test rules with historical data

#### Rule Performance
- View trigger history to see how often rules fire
- Check alert creation rate (not all triggers create alerts due to cooldowns)
- Adjust thresholds based on false positive rates

### Best Practices

#### Start Simple
- Begin with 1-2 rules focused on specific scenarios
- Use medium severity for testing
- Set longer cooldowns (60+ minutes) initially

#### Fine-tune Thresholds
- Monitor trigger history for a week
- Adjust thresholds based on actual data patterns
- Balance sensitivity vs. noise

#### Use Targeting Wisely
- Specific keywords reduce false positives
- Geographic targeting helps with regional events
- Categories help focus on relevant content types

#### Notification Strategy
- Critical alerts: Email + Desktop
- Medium alerts: Desktop only
- Low alerts: Dashboard only (no notifications)

### Troubleshooting

#### Rule Not Triggering
- Check if the rule is **enabled**
- Verify **target keywords** match actual trend data
- Confirm **geo scope** includes monitored regions
- Review **threshold values** against real data

#### Too Many False Alerts
- Increase **threshold values**
- Add more specific **target keywords**
- Extend **cooldown minutes**
- Use **categories** to narrow focus

#### Missing Notifications
- Check **notification settings** are enabled
- Verify **email recipients** are correct
- Ensure desktop notifications are allowed in browser

### Advanced Features

#### Rule Metadata
- Store additional configuration in JSON format
- Define time windows, patterns, or custom logic
- Extend rules with custom parameters

#### Trigger History
- Every rule trigger is logged with:
  - Exact values that triggered the rule
  - Whether an alert was created
  - Timestamp and context information
- Use this data to optimize rule performance

#### Integration with Main Alerts
- Rule-generated alerts work with all existing features:
  - Escalation rules
  - Silence settings
  - Feedback and post-mortems
  - Evidence chains and analytics

Alert Rules give you proactive control over trend monitoring, complementing the automatic anomaly detection system with your domain expertise and specific monitoring needs.

## Project Status & Roadmap

This section provides a comprehensive overview of completed features, current priorities, and future development plans based on our TODO roadmap.

### ✅ Completed Features

#### Core System Infrastructure
- **Multi-Source Data Ingestion**: Google Trends, Wikipedia, Reddit, GDELT integration
- **Real-time Anomaly Detection**: STL decomposition, Isolation Forest, CUSUM algorithms
- **Ensemble Detection Pipeline**: Combined statistical and semantic analysis
- **WebSocket Real-time Updates**: Live dashboard updates and notifications
- **Database Architecture**: PostgreSQL with 4 schemas (ingestion, signal, alert, backtest)
- **API Layer**: FastAPI with 28+ endpoints, JWT authentication, CORS
- **Dashboard**: Next.js 14 with React 18, TypeScript, TailwindCSS
- **Alert Management**: CRUD operations, escalation rules, silence settings
- **Backtesting Engine**: Historical replay and strategy validation

#### Signal Quality & Risk Management
- **Signal Decay & Half-Life Tracking**: Estimated half-life calculation and decay curve visualization
- **Counter-Signal Engine**: Active search for disconfirming data and opposing trends
- **Narrative Saturation Detector**: BERT-based topic modeling to detect oversaturated narratives
  - Measures trend progression from "early" to "mainstream"
  - Detects media overexposure and retail awareness peaks
  - Implements alert downgrades and trading size auto-reduction
  - Halts execution when saturation indicates topping cycles

#### User Experience & Trust
- **Alert Rules System**: Custom condition-based alert generation
- **Evidence Builder**: Comprehensive evidence chains for alerts
- **Feedback System**: User feedback integration for model improvement
- **Watchlist Management**: Custom keyword and category monitoring
- **Dashboard Analytics**: Charts, metrics, and performance tracking

### 🚧 In Progress / High Priority

#### Decision Transparency & Trust
- **"Why Not Trade?" Explanations**: Generate explanations for non-action decisions
- **Confidence Decomposition**: Break confidence into data quality, model agreement, historical similarity
- **Replay Mode (Post-Mortem Simulator)**: System state rewind after alerts/trades for debugging and audits

#### Trading Survival & Capital Protection
- **Kill-Switches**: Anomaly instability, signal volatility, confidence collapse triggers
- **Gradual Autonomy Ramp**: Progressive feature unlocking based on statistical proof
- **Capital Memory**: Track past drawdowns and implement size reduction in similar regimes

### 📋 Medium Priority Features

#### Research & Edge-Compounding
- **Signal Lineage Tracking**: Maintain ancestry records for data sources and transformations
- **Synthetic "What-If" Events**: Generate hypothetical trend spikes for testing
- **Meta-Learning on Failure**: Classify failure types and retrain guardrails

#### User Experience Enhancements
- **Alert Throttling**: Monitor alert volume and implement notification slowing/batching
- **"Trust Meter" per Feature**: Track and display feature help vs mislead rates

### 🔮 Future Roadmap (Optional but Powerful)

#### Market Reflexivity Monitor
- Track self-created price action from alerts and amplification
- Monitor similar platform effects and social feedback loops
- Downgrade signals when reflexivity risk is high

#### Security & Compliance
- End-to-end encryption for sensitive trading data
- Comprehensive audit logging and regulatory compliance
- Multi-factor authentication and role-based access controls

#### Scalability & Infrastructure
- Horizontal scaling with Kubernetes orchestration
- Advanced monitoring with ELK stack
- API rate limiting and circuit breakers

#### Advanced Analytics
- A/B testing framework for trading strategies
- Monte Carlo simulation for portfolio stress testing
- Multi-modal fusion and causal inference

### 🎯 Top 3 Priority Features (Highest Impact/Lowest Effort)
1. **Replay Mode** - Post-mortem simulator for debugging and confidence building
2. **"Why Not Trade?" Explanations** - Build user trust through responsible AI behavior
3. **Kill-Switches** - Automatic system pause for anomalous conditions

### 📊 Success Metrics Tracking
- User engagement (daily/weekly active users)
- Alert accuracy and response times (<200ms API response)
- System performance and data quality (>95% accuracy, >98% completeness)
- Feature adoption rates and customer satisfaction
- Trading performance metrics (Sharpe ratio, max drawdown, win rate)
- AI agent confidence scores and override rates

### 🗓️ Development Timeline
- **Phase 1-4 (Foundation)**: Database schemas, order management, market data, portfolio tracking ✅
- **Phase 5-6 (Safety)**: Paper trading simulation, risk management controls 🚧
- **Phase 7-8 (Intelligence)**: Strategy development, AI autonomy with RL 📋
- **Phase 9-10 (Production)**: Advanced analytics, live deployment with safety controls 🔮

This roadmap represents a comprehensive approach to building a responsible, transparent, and effective AI trading system. The focus remains on signal quality, capital protection, and user trust while continuously expanding analytical capabilities.
