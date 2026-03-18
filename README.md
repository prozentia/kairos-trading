# Kairos Trading

Bot de trading automatise multi-paires, event-driven, concu pour remplacer le legacy BTC Sniper Bot par une architecture moderne et scalable.

**Stack** : Python 3.12 + FastAPI + React 19 + PostgreSQL 16 + Redis 7 + Binance API + AI Agent (OpenRouter)

**Production** : `kairos.prozentia.com` — VPS 158.220.103.131

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KAIROS TRADING                          │
├──────────┬──────────┬──────────┬──────────┬─────────┬──────────┤
│ Frontend │   API    │  Engine  │ AI Agent │Notifier │   DB     │
│ React 19 │ FastAPI  │  Runner  │ Telegram │  Redis  │ Postgres │
│ port 3002│ port 8002│ asyncio  │ OpenRouter│ pub/sub │ port 5432│
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬────┴────┬─────┘
     │          │          │          │          │         │
     │    REST/WS    Binance WS   LLM API   Redis Sub  SQLAlchemy
     │          │     + REST      (Claude)     │      (async)
     └──────────┴──────────┴──────────┴──────────┴─────────┘
```

### Principe de separation

| Couche | Role | Regle |
|--------|------|-------|
| `core/` | Algorithmes purs (indicateurs, strategies, risque) | Zero I/O, zero import externe |
| `adapters/` | Binance, PostgreSQL, Redis, notifications | I/O isole, interfaces abstraites |
| `engine/` | Orchestrateur temps reel | Connecte core + adapters |
| `api/` | REST + WebSocket | Frontend ↔ Backend |
| `ai_agent/` | Agent conversationnel Telegram | Tool calling via LLM |
| `notifier/` | Dispatch notifications multi-canal | Redis pub/sub listener |

---

## Stack technique

### Backend
- **Python 3.12+** — type hints stricts, mypy
- **FastAPI 0.110+** — REST API async
- **SQLAlchemy 2.0+** (async) + Alembic migrations
- **PostgreSQL 16** — base de donnees principale
- **Redis 7** — cache, pub/sub, message broker
- **python-binance** — REST + WebSocket Binance
- **asyncio** — architecture event-driven

### Frontend
- **React 19** + TypeScript 5.9
- **Vite 7.2** — build tool
- **TailwindCSS 4.1** + **shadcn/ui**
- **ApexCharts** — graphiques temps reel
- **TanStack Query** — data fetching
- **React Router 7.9**

### AI & Notifications
- **OpenRouter API** — 400+ modeles LLM (defaut: Claude Sonnet 4)
- **python-telegram-bot 21+** — agent interactif + notifications
- **Firebase Admin SDK** — push notifications mobile
- **SMTP** — email

### Mobile (WIP)
- **React Native 0.76** + **Expo 52**

---

## Services Docker (7 containers)

| Container | Image | Port | Role |
|-----------|-------|------|------|
| `kairos-db` | postgres:16 | 5432 | Base de donnees |
| `kairos-redis` | redis:7 | 6379 | Cache + pub/sub |
| `kairos-api` | python:3.12 | 8002 | API REST + WebSocket |
| `kairos-engine` | python:3.12 | — | Moteur de trading |
| `kairos-frontend` | node:20 + nginx | 3002 | Interface web |
| `kairos-ai-agent` | python:3.12 | — | Agent Telegram |
| `kairos-notifier` | python:3.12 | — | Dispatcher notifications |

---

## Structure du projet

```
kairos/
├── core/                          # Algorithmes purs (zero I/O)
│   ├── models.py                  # Dataclasses: Candle, Signal, Position, Trade
│   ├── indicators/                # 25+ indicateurs techniques
│   │   ├── base.py               # Interface BaseIndicator
│   │   ├── registry.py           # Auto-discovery @register
│   │   ├── rsi.py, ema.py, bollinger.py, ichimoku.py ...
│   ├── strategy/
│   │   ├── loader.py             # Parse strategies JSON
│   │   ├── evaluator.py          # Evaluation conditions
│   │   └── filters.py            # Filtrage post-signal
│   ├── decision/
│   │   ├── aggregator.py         # Aggregation multi-indicateurs
│   │   ├── confidence_scorer.py  # Score de confiance
│   │   └── setup_classifier.py   # Classification setup
│   ├── risk/
│   │   ├── position.py           # Gestion positions
│   │   ├── sizing.py             # Kelly criterion
│   │   ├── portfolio.py          # Risque portefeuille
│   │   └── risk_gate.py          # Validation pre-trade
│   └── timeframe/
│       ├── buffer.py             # Buffer candles
│       └── aggregator.py         # Multi-timeframe
│
├── adapters/                      # I/O externe
│   ├── exchanges/
│   │   ├── base.py               # Interface abstraite
│   │   ├── binance_ws.py         # WebSocket streams
│   │   └── binance_rest.py       # REST API orders
│   ├── database/
│   │   ├── models.py             # ORM SQLAlchemy
│   │   ├── repository.py         # Abstraction DB
│   │   └── migrations/           # Alembic
│   ├── cache/redis.py            # Client Redis
│   └── notifications/
│       ├── telegram.py
│       ├── firebase.py
│       └── email.py
│
├── engine/                        # Orchestrateur
│   ├── main.py                   # Entry point
│   ├── runner.py                 # Event loop principal
│   ├── executor.py               # Execution ordres
│   ├── pipeline.py               # Pipeline de donnees
│   ├── monitor.py                # Health monitoring
│   └── safety.py                 # Securite d'urgence
│
├── api/                           # FastAPI
│   ├── main.py                   # App factory, CORS, routers
│   ├── auth/                     # JWT + bcrypt
│   ├── middleware/               # Rate limiting
│   ├── routers/                  # 12 routers, 50+ endpoints
│   └── schemas/                  # Pydantic models
│
├── ai_agent/                      # Agent IA Telegram
│   ├── agent.py                  # KairosAgent + tool calling
│   ├── provider.py               # Client OpenRouter
│   ├── tools.py                  # 10+ outils disponibles
│   ├── telegram_handler.py       # Integration Telegram
│   └── analysts/                 # Analystes specialises
│       ├── technical_analyst.py
│       ├── momentum_analyst.py
│       ├── risk_analyst.py
│       └── context_analyst.py
│
├── notifier/                      # Notifications
│   ├── dispatcher.py             # Redis pub/sub listener
│   └── channels/                 # Telegram, Firebase, Email
│
├── frontend/                      # React 19 + Vite
│   ├── src/
│   │   ├── pages/                # Dashboard, Strategies, Trades...
│   │   ├── components/           # UI components (shadcn)
│   │   ├── services/             # API client
│   │   └── hooks/                # Custom hooks
│   └── nginx.conf                # Reverse proxy
│
├── mobile/                        # React Native (WIP)
├── scripts/                       # Scripts utilitaires
├── docker-compose.yml             # Dev
├── docker-compose.prod.yml        # Production
└── docker-compose.override.yml    # Overrides dev (ports 3002/8002)
```

---

## API Endpoints

### Authentication (`/auth`)
| Methode | Route | Description |
|---------|-------|-------------|
| POST | `/register` | Creer un compte |
| POST | `/login` | Connexion (JWT) |
| POST | `/refresh` | Rafraichir le token |
| GET | `/me` | Profil utilisateur |
| PUT | `/me` | Modifier le profil |
| POST | `/change-password` | Changer le mot de passe |

### Trades (`/trades`)
| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Liste avec pagination et filtres |
| GET | `/stats` | Statistiques agregees (win rate, P&L, Sharpe) |
| GET | `/export/csv` | Export CSV |
| GET | `/{id}` | Detail d'un trade |
| POST | `/record-complete` | Enregistrement par l'engine |
| POST | `/{id}/journal` | Ajouter une note journal |

### Strategies (`/strategies`)
| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Liste des strategies |
| POST | `/` | Creer une strategie |
| PUT | `/{id}` | Modifier |
| DELETE | `/{id}` | Supprimer |
| POST | `/{id}/activate` | Activer pour le trading |
| POST | `/{id}/deactivate` | Desactiver |
| POST | `/{id}/duplicate` | Cloner |
| POST | `/{id}/validate` | Valider la configuration |

### Portfolio (`/portfolio`)
| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Vue d'ensemble |
| GET | `/positions` | Positions ouvertes |
| GET | `/allocation` | Allocation par actif |
| GET | `/risk-metrics` | Drawdown, Sharpe, Sortino |
| GET | `/correlation-matrix` | Correlations entre paires |

### Market (`/market`)
| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/price/{pair}` | Prix courant |
| GET | `/prices` | Tous les prix actifs |
| GET | `/candles/{pair}` | Historique OHLCV |
| GET | `/ticker/{pair}` | Stats 24h |
| GET | `/orderbook/{pair}` | Carnet d'ordres |

### Alerts (`/alerts`)
| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/` | Alertes actives |
| POST | `/` | Creer une alerte |
| PUT | `/{id}` | Modifier |
| DELETE | `/{id}` | Supprimer |
| GET | `/history` | Historique declenchements |

### Bot (`/bot`)
| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/status` | Statut actuel |
| POST | `/start` | Demarrer le bot |
| POST | `/stop` | Arreter |
| POST | `/restart` | Redemarrer |
| GET | `/config` | Configuration |
| PUT | `/config` | Modifier la config |
| GET | `/logs` | Logs recents |

### Backtests (`/backtests`)
| Methode | Route | Description |
|---------|-------|-------------|
| POST | `/` | Lancer un backtest |
| GET | `/{id}` | Resultats |
| GET | `/{id}/status` | Progression |
| POST | `/compare` | Comparer plusieurs backtests |

### AI Reports (`/ai-reports`)
| Methode | Route | Description |
|---------|-------|-------------|
| GET | `/latest` | Dernier rapport |
| POST | `/generate` | Generer un rapport (async) |
| GET | `/history` | Historique des rapports |

### WebSocket (`/ws`)
| Route | Description |
|-------|-------------|
| `/ws/market/{pair}` | Prix temps reel |
| `/ws/trades` | Notifications trades |
| `/ws/bot-status` | Statut du bot |
| `/ws/positions` | MAJ positions |
| `/ws/logs` | Stream logs |
| `/ws/notifications` | Notifications generales |

---

## Base de donnees

### Tables PostgreSQL

| Table | Colonnes principales |
|-------|---------------------|
| `users` | id (UUID), username, email, hashed_password, preferences |
| `trades` | id, pair, side, entry/exit_price, quantity, pnl_usdt, pnl_pct, strategy_name, status |
| `strategies` | id, name, json_definition, is_active, total_trades, winning_trades, total_pnl |
| `pairs` | symbol, exchange, is_active, min_qty, step_size, tick_size |
| `alerts` | id, user_id, type, condition_json, channels_json, triggered_at |
| `daily_stats` | date, pair, total_trades, winning_trades, pnl_usdt, max_drawdown |
| `ai_reports` | report_type (daily/weekly/custom), content, metrics_json, model_used |
| `backtests` | strategy_id, pair, start/end_date, results_json |
| `trade_journal` | trade_id, notes, tags_json, screenshots_json |
| `notifications` | user_id, type, channel, title, body, is_read |

---

## Indicateurs techniques (25+)

RSI, EMA, SMA, Bollinger Bands, MACD, Ichimoku Cloud, ATR, Stochastic, OBV, VWAP, ADX, CCI, Williams %R, Parabolic SAR, Fibonacci Retracements, Donchian Channels, Keltner Channels, Heikin-Ashi, Supertrend, Market Structure Break (MSB), Order Blocks, Fair Value Gaps, Volume Profile, Momentum, Rate of Change

Chaque indicateur : 1 fichier, 1 test, auto-enregistrement via `@register`.

---

## Gestion du risque

| Mecanisme | Description |
|-----------|-------------|
| **Position Sizing** | Kelly criterion, niveaux de confiance (CRAWL/WALK/RUN) |
| **Risk Gate** | Validation pre-trade (spread, slippage, confiance, exposition) |
| **Stop-Loss** | Double : local + serveur Binance |
| **Trailing Stop** | Activation et distance configurables |
| **Budget cap** | Max positions, perte journaliere max, drawdown max |
| **Dry Run** | Mode simulation sans ordres reels |

---

## Agent IA (Telegram)

Agent conversationnel avec acces a 10+ outils via function calling :

| Outil | Description |
|-------|-------------|
| `get_bot_status` | Etat du bot, uptime, positions |
| `get_trade_history` | Historique trades avec filtres |
| `get_trade_stats` | Win rate, P&L, Sharpe, Sortino |
| `get_portfolio` | Balance, exposition, positions |
| `get_market_analysis` | Analyse technique multi-timeframe |
| `list_strategies` | Strategies avec statut |
| `get_strategy_detail` | Configuration complete |
| `run_backtest` | Test historique |
| `get_alerts` | Alertes actives et declenchees |
| `create_alert` | Creer une alerte prix |
| `get_risk_metrics` | Drawdown, exposition, pertes |

Modele par defaut : **Claude Sonnet 4** via OpenRouter.

---

## Notifications

Architecture Redis pub/sub multi-canal :

| Canal Redis | Evenement |
|-------------|-----------|
| `kairos:trades` | BUY, SELL, Stop-Loss |
| `kairos:alerts` | Declenchement d'alertes |
| `kairos:system` | Start/Stop/Restart bot |
| `kairos:ai` | Rapport IA genere |

**Canaux de dispatch** : Telegram, Firebase Push, Email, In-app WebSocket.

---

## Installation

### Prerequis
- Docker + Docker Compose
- Cle API Binance (testnet ou live)
- Token bot Telegram (optionnel)
- Cle OpenRouter (optionnel)

### Lancement

```bash
# Cloner
git clone https://github.com/prozentia/kairos-trading.git
cd kairos-trading

# Configurer
cp .env.example .env
# Remplir les variables dans .env

# Lancer (dev)
docker compose up -d

# Lancer (production)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Ports

| Port | Service | Environnement |
|------|---------|---------------|
| 3002 | Frontend | Dev |
| 8002 | API | Dev |
| 443/80 | Traefik (frontend) | Production |
| 5432 | PostgreSQL | Interne |
| 6379 | Redis | Interne |

---

## Variables d'environnement

```env
# PostgreSQL
POSTGRES_DB=kairos
POSTGRES_USER=kairos
POSTGRES_PASSWORD=change_me

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET=random_64_char_string
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15

# Binance
BINANCE_API_KEY=
BINANCE_API_SECRET=
BINANCE_TESTNET=true

# Engine
KAIROS_DRY_RUN=true
KAIROS_TESTNET=true
KAIROS_PAIRS=BTCUSDT,ETHUSDT
KAIROS_STRATEGY_TIMEFRAME=5m
KAIROS_CAPITAL_PER_PAIR=100.0
KAIROS_MAX_POSITIONS=3
KAIROS_MAX_DAILY_LOSS_PCT=5.0
KAIROS_MAX_DRAWDOWN_PCT=15.0

# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# AI Agent
OPENROUTER_API_KEY=
OPENROUTER_MODEL=anthropic/claude-sonnet-4

# CORS
CORS_ORIGINS=http://localhost:5173,https://kairos.prozentia.com
```

---

## Commandes utiles

```bash
# Logs d'un service
docker logs kairos-engine --tail=50 -f

# Statut des containers
docker compose ps

# Migration DB
docker exec kairos-api alembic upgrade head

# Rebuild un service
docker compose build --no-cache api
docker compose up -d api

# Backup PostgreSQL
docker exec kairos-db pg_dump -U kairos kairos > backup.sql

# Redis CLI
docker exec -it kairos-redis redis-cli
```

---

## Conventions

- **Francais** : messages, commits, documentation
- **Anglais** : code, variables, fonctions
- **Type hints** : stricts sur `core/`, mypy active
- **Tests** : pytest pour tous les modules
- **Fichiers** : < 300 lignes
- **1 indicateur = 1 fichier** : auto-discovery via `@register`
- **Zero I/O dans `core/`** : algorithmes purs uniquement
