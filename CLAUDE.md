# CLAUDE.md - Kairos Trading

## IMPORTANT - Langue
**Toujours repondre en FRANCAIS.**
- Messages et explications: Francais
- Commentaires de code: Anglais
- Variables/fonctions: Anglais
- Commits: Francais (format: `type(scope): description`)

## Projet

Kairos Trading - Plateforme de trading automatise multi-paires, event-driven.
Remplacement complet de BTC Sniper Bot avec architecture propre des le depart.

## Architecture

```
core/       → Pur Python, ZERO I/O, ZERO dependance externe. Testable unitairement.
engine/     → Orchestre core + adapters en mode live (asyncio)
adapters/   → I/O : Binance WS/REST, PostgreSQL, Redis, Telegram, Firebase
api/        → FastAPI backend REST + WebSocket
ai_agent/   → Agent IA Telegram + OpenRouter
notifier/   → Service de notifications (Telegram, Push, Email)
frontend/   → React (WowDash template) + TypeScript + Tailwind + shadcn/ui
mobile/     → React Native + Expo (a faire APRES le bot)
tests/      → pytest pour core/api/integration, Playwright pour e2e
```

**Regle d'or** : `core/` n'importe JAMAIS depuis `adapters/`, `engine/`, `api/` ou autre.
Le flux est toujours : `adapters → engine → core` (dependency inversion).

## Commandes

```bash
# Dev - lancer les services
docker compose up -d                    # PostgreSQL + Redis
pytest tests/core/ -v                   # Tests core
pytest tests/api/ -v                    # Tests API
python -m engine.main                   # Lancer le trading engine
uvicorn api.main:app --reload --port 8000  # Lancer l'API

# Docker production
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

## Conventions

- Fichiers < 300 lignes (sinon, decouper)
- Chaque indicateur = 1 fichier dans `core/indicators/`
- Chaque indicateur a un test dans `tests/core/test_indicators/`
- NE JAMAIS coder sans tests
- NE JAMAIS modifier `core/` sans faire passer les tests
- Typage strict (mypy) sur `core/`

## Base de donnees

- **Dev** : PostgreSQL dans Docker (port 5432)
- **Prod** : PostgreSQL dans Docker (meme)
- **ORM** : SQLAlchemy 2.0 + Alembic pour les migrations
- **Tables** : users, trades, strategies, pairs, alerts, daily_stats, ai_reports, backtests, trade_journal, notifications

## VPS Production

- **IP** : 158.220.103.131
- **Domaine** : kairos.prozentia.com
- **Acces SSH** : `ssh root@158.220.103.131`
- **Chemin** : /opt/kairos-trading
- **Docker** : 7 containers (db, redis, api, engine, frontend, ai-agent, notifier)

## Etat actuel

- [x] Structure du projet creee
- [x] Core models (Candle, Signal, Position, Trade)
- [x] BaseIndicator interface
- [x] IndicatorRegistry
- [x] Fixtures de test (500 bougies BTC)
- [ ] Indicateurs tendance (0/8)
- [ ] Indicateurs momentum (0/7)
- [ ] Indicateurs volatilite (0/4)
- [ ] Indicateurs volume (0/3)
- [ ] Indicateurs speciaux (0/3)
- [ ] Evaluateur de strategies
- [ ] Filtres post-signal
- [ ] Risk management
- [ ] Timeframe aggregator
- [ ] Adapter Binance WebSocket
- [ ] Adapter Binance REST
- [ ] Adapter PostgreSQL
- [ ] Adapter Redis
- [ ] Engine runner
- [ ] API FastAPI
- [ ] Frontend
- [ ] Mobile

## Specs completes

Voir `KAIROS_TRADING_SPECS.md` (bot + web) et `KAIROS_MOBILE_SPECS.md` (mobile).
