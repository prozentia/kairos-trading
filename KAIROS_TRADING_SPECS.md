# KAIROS TRADING - Cahier des Charges Complet

> **Kairos** (grec ancien) : *le moment opportun, l'instant decisif* - L'art de saisir le bon moment pour agir.

---

## Table des Matieres

1. [Vision et Objectifs](#1-vision-et-objectifs)
2. [Specifications Fonctionnelles](#2-specifications-fonctionnelles)
3. [Wireframes / UX-UI](#3-wireframes--ux-ui)
4. [Architecture Technique](#4-architecture-technique)
5. [Schema de Base de Donnees](#5-schema-de-base-de-donnees)
6. [Contrats API](#6-contrats-api)
7. [Strategie Mobile](#7-strategie-mobile)
8. [Securite](#8-securite)
9. [Testing et Qualite](#9-testing-et-qualite)
10. [Infrastructure et DevOps](#10-infrastructure-et-devops)
11. [Migration depuis BTC Sniper Bot](#11-migration-depuis-btc-sniper-bot)

---

## 1. Vision et Objectifs

### 1.1 Vision

Kairos Trading est une **plateforme de trading automatise** multi-paires, multi-strategies, accessible depuis le web et le mobile. Contrairement a BTC Sniper Bot (monolithe mono-paire), Kairos est concu des le depart comme un **produit complet, scalable et event-driven**.

### 1.2 Ce que Kairos garde du bot actuel (acquis)

| Feature | Statut |
|---------|--------|
| Strategy Builder visuel (20 indicateurs, AND/OR/NOT) | **Conserve et ameliore** |
| Hot-reload des strategies | **Conserve** |
| Notifications Telegram | **Conserve et etendu** |
| Agent IA conversationnel | **Conserve et etendu** |
| Rapports IA | **Conserve et etendu** |
| Double stop-loss (local + Binance serveur) | **Conserve** |
| Detection position existante au demarrage | **Conserve** |
| DRY-RUN / LIVE toggle | **Conserve** |
| Watchdog auto-restart | **Conserve** |
| Dashboard WowDash + shadcn/ui | **Conserve (meme template)** |

### 1.3 Ce que Kairos ajoute (nouveautes)

| Feature | Description |
|---------|-------------|
| **Architecture event-driven** | WebSocket Binance au lieu du polling 10s |
| **Multi-paires** | BTC, ETH, SOL, BNB, etc. simultanement |
| **Multi-positions** | Plusieurs trades ouverts en parallele |
| **Core engine partage** | Meme moteur pour live, backtest et paper trading |
| **PostgreSQL** | Remplace SQLite, supporte le multi-acces |
| **WebSocket temps reel** | Prix et positions pousses vers le frontend |
| **App mobile** | React Native, notifications push |
| **Calcul incremental** | Indicateurs mis a jour bougie par bougie, pas recalcules |
| **Backtester realiste** | Slippage, frais, latence simulee |
| **Paper trading parallele** | Tester N strategies en meme temps sans risque |
| **Multi-exchange** | Binance + Bybit + OKX (architecture prete) |
| **CI/CD** | GitHub Actions : lint + tests + deploy automatique |
| **Monitoring** | Prometheus + Grafana |
| **Risk management portfolio** | Exposure max, drawdown max, correlation inter-paires |
| **Journal de trading** | Notes, screenshots, tags par trade |
| **Alertes avancees** | Prix, indicateurs, P&L, drawdown — Telegram/Push/Email |
| **Mode copy-trading** | Partager ses strategies (futur) |

### 1.4 Principes d'Architecture

```
1. EVENT-DRIVEN  : Pas de polling. Le marche pousse les donnees.
2. CORE ISOLE    : Le moteur de trading n'a aucune dependance I/O.
3. TESTABLE      : Chaque module est testable unitairement.
4. MOBILE-FIRST  : L'API est concue pour le mobile des le jour 1.
5. SCALABLE      : Ajouter une paire ou un exchange = config, pas code.
```

---

## 2. Specifications Fonctionnelles

### 2.1 Module : Trading Engine (Core)

Le coeur du systeme. **Pur Python, zero I/O, zero dependance externe.**

#### 2.1.1 Gestion des Bougies

| Feature | Description |
|---------|-------------|
| Reception bougie | Via callback `on_candle(candle)` - agnostique de la source |
| Multi-timeframe | Aggregation automatique 1m → 3m → 5m → 15m → 1h → 4h → 1d |
| Buffer circulaire | Stocke les N dernieres bougies par timeframe (configurable) |
| Heikin Ashi | Calcul automatique en parallele des bougies classiques |

#### 2.1.2 Indicateurs Techniques (25)

Tous les indicateurs sont **incrementaux** : mis a jour a chaque nouvelle bougie sans recalculer tout l'historique.

**Tendance (8)**

| # | Indicateur | Cle | Params | Operateurs |
|---|-----------|-----|--------|------------|
| 1 | EMA | `ema` | period | price_above, price_below, crosses_above, crosses_below |
| 2 | SMA | `sma` | period | price_above, price_below, crosses_above, crosses_below |
| 3 | EMA Cross | `ema_cross` | fast, mid, slow | bullish_cross, bearish_cross |
| 4 | Supertrend | `supertrend` | atr_period, factor | bullish, bearish, crosses_bullish, crosses_bearish |
| 5 | Heikin Ashi | `heikin_ashi` | - | is_green, is_red, reversal_up, reversal_down, consecutive_green, consecutive_red |
| 6 | Parabolic SAR | `parabolic_sar` | af_start, af_increment, af_max | bullish, bearish, crosses_bullish, crosses_bearish |
| 7 | Donchian | `donchian` | period | above_upper, below_lower, breakout_up, breakout_down |
| 8 | Ichimoku | `ichimoku` | tenkan, kijun, senkou_b | above_cloud, below_cloud, tk_cross_bullish, tk_cross_bearish |

**Momentum (7)**

| # | Indicateur | Cle | Params | Operateurs |
|---|-----------|-----|--------|------------|
| 9 | RSI | `rsi` | period | >, <, crosses_above, crosses_below, between, divergence_bullish, divergence_bearish |
| 10 | MACD | `macd` | fast, slow, signal | crosses_above_signal, crosses_below_signal, histogram_positive, histogram_negative |
| 11 | Stochastic | `stochastic` | k_period, d_period, smooth | oversold, overbought, crosses_above, crosses_below |
| 12 | Stochastic RSI | `stochastic_rsi` | rsi_period, stoch_period, k_smooth, d_smooth | oversold, overbought, crosses_above, crosses_below |
| 13 | CCI | `cci` | period | >, <, crosses_above, crosses_below |
| 14 | ROC | `roc` | period | >, <, crosses_above, crosses_below |
| 15 | TSI | `tsi` | long, short, signal | >, <, crosses_above_signal, crosses_below_signal |

**Volatilite (4)**

| # | Indicateur | Cle | Params | Operateurs |
|---|-----------|-----|--------|------------|
| 16 | Bollinger Bands | `bollinger` | period, std_dev | touches_upper, touches_lower, above_upper, below_lower, squeeze, expansion, bandwidth_above, bandwidth_below |
| 17 | ATR | `atr` | period | >, <, expanding, contracting |
| 18 | ADX/DMI | `adx_dmi` | period | adx_above, adx_below, di_plus_above_minus, di_minus_above_plus |
| 19 | Keltner Channel | `keltner` | ema_period, atr_period, multiplier | above_upper, below_lower, squeeze_with_bb |

**Volume (3)**

| # | Indicateur | Cle | Params | Operateurs |
|---|-----------|-----|--------|------------|
| 20 | Volume | `volume` | period | above_average, below_average, spike, climax |
| 21 | VWAP | `vwap` | deviation_1, deviation_2 | price_above, price_below, above_upper_band, below_lower_band |
| 22 | Chaikin Money Flow | `chaikin_money_flow` | period | >, <, positive, negative |

**Special (3)**

| # | Indicateur | Cle | Params | Operateurs |
|---|-----------|-----|--------|------------|
| 23 | MSB Glissant | `msb_glissant` | bb_proximity_pct, ha_red_grace | break_detected |
| 24 | Order Block | `order_block` | lookback, min_volume_ratio | bullish_ob_near, bearish_ob_near |
| 25 | Fair Value Gap | `fvg` | min_gap_pct | bullish_fvg_near, bearish_fvg_near |

#### 2.1.3 Evaluation des Strategies

| Feature | Description |
|---------|-------------|
| Format JSON | Meme format que le bot actuel (entry_conditions, exit_conditions, risk_management, filters) |
| Groupes recursifs | AND / OR / NOT imbriques sans limite |
| Multi-timeframe conditions | Une condition peut referencer un timeframe different (ex: RSI(14) sur 1h) |
| Variables dynamiques | `atr_value`, `bb_bandwidth` utilisables dans les valeurs (ex: stop_loss = 2 * ATR) |
| Conditions temporelles | `consecutive_green >= 3`, `time_in_position > 30min` |

#### 2.1.4 Filtres Post-Signal

| Filtre | Description | Params |
|--------|-------------|--------|
| EMA Trend | Bloque BUY si prix < EMA sur un TF superieur | period, timeframe |
| Trading Hours | Bloque BUY en dehors des heures | start_utc, end_utc, days[] |
| Loss Cooldown | Pause apres un stop-loss | minutes |
| Max Daily Trades | Limite le nombre de trades par jour | max_count |
| Max Daily Loss | Stop trading si perte > seuil | max_loss_pct |
| Correlation Filter | Bloque si asset correle est en chute | correlated_pair, threshold |
| Volatility Filter | Bloque si volatilite trop haute/basse | atr_min, atr_max |

#### 2.1.5 Gestion des Positions

| Feature | Description |
|---------|-------------|
| Stop-Loss fixe | % sous le prix d'entree |
| Stop-Loss dynamique ATR | SL = entry - (N * ATR) |
| Trailing Stop | Activation a X% de profit, suit a Y% de distance |
| Trailing ATR | Distance du trailing = N * ATR (s'adapte a la volatilite) |
| Take-Profit fixe | Vente a X% de profit |
| Take-Profit partiel | Vente de N% de la position a chaque palier |
| Take-Profit multi-paliers | Palier 1: 50% a +1%, Palier 2: 30% a +2%, Palier 3: 20% trailing |
| Break-even auto | Deplace le SL au prix d'entree apres X% de profit |
| Sortie par signal | La strategie peut generer un SELL_SIGNAL |
| Sortie d'urgence | EMERGENCY_SELL sur HA rouge (ou autre condition) |
| Time-based exit | Vente si position ouverte > N heures sans profit |
| SL serveur exchange | Stop-loss place cote Binance (protection crash) |

#### 2.1.6 Risk Management Portfolio

| Feature | Description |
|---------|-------------|
| Exposure max | Capital total engage ne depasse pas X% |
| Max positions simultanees | Limite configurable (1 a 10) |
| Max drawdown journalier | Arret du trading si drawdown > X% |
| Max drawdown total | Arret si drawdown depuis le peak > X% |
| Position sizing dynamique | Taille basee sur ATR ou % du capital |
| Kelly criterion | Sizing optimal base sur le win rate et risk/reward |
| Correlation check | Evite d'ouvrir 2 positions sur des actifs tres correles |

### 2.2 Module : Market Data

#### 2.2.1 WebSocket Streams

| Stream | Donnees | Usage |
|--------|---------|-------|
| Kline (1m) | OHLCV en temps reel | Indicateurs, signaux |
| Ticker 24h | Prix, volume 24h, variation | Dashboard |
| Book Ticker | Best bid/ask | Precision entree |
| User Data | Ordres, fills, solde | Suivi positions |

#### 2.2.2 Aggregation Multi-Timeframe

```
WebSocket 1m → buffer 1m
  Toutes les 3 bougies 1m → genere une bougie 3m
  Toutes les 5 bougies 1m → genere une bougie 5m
  Toutes les 15 bougies 1m → genere une bougie 15m
  Toutes les 60 bougies 1m → genere une bougie 1h
  Toutes les 240 bougies 1m → genere une bougie 4h
```

Chaque nouvelle bougie aggregee declenche l'evaluation de la strategie sur ce timeframe.

#### 2.2.3 Historique

| Feature | Description |
|---------|-------------|
| Preload au demarrage | Charge N bougies historiques pour initialiser les indicateurs |
| Cache en memoire | Buffer circulaire par paire et timeframe |
| Persistance optionnelle | Export en CSV/Parquet pour le backtester |

### 2.3 Module : Strategy Builder

#### 2.3.1 Fonctionnalites UI

| Feature | Description |
|---------|-------------|
| Creation visuelle | Drag & drop de conditions, choix indicateurs/operateurs |
| Edition en temps reel | Preview de la strategie pendant l'edition |
| Validation instantanee | Feedback immediat sur les erreurs |
| Duplication | Copier une strategie pour la modifier |
| Versionning | Historique des modifications d'une strategie |
| Import/Export JSON | Partager des strategies |
| Templates | Strategies pre-configurees (starter pack) |
| Conditions imbriquees | Groupes AND/OR drag & droppables |
| Conditions de sortie | Section dediee avec ses propres indicateurs |
| Filtres configurables | Section filtres avec toggles + params |
| Risk management | Sliders visuels pour SL, TP, trailing |
| Preview en temps reel | Montre sur un mini-graphique ou les signaux seraient apparus |
| Multi-timeframe visual | Dropdown timeframe par condition |

#### 2.3.2 Workflow

```
Creer → Editer → Sauvegarder → Valider → Backtester → Activer
                                            ↓
                                     Paper Trading (optionnel)
                                            ↓
                                     Activer en LIVE
```

#### 2.3.3 Backtest Integre

| Feature | Description |
|---------|-------------|
| Periode configurable | 1 jour a 365 jours |
| Frais simules | Frais maker/taker Binance (0.1%) |
| Slippage simule | 0.01% a 0.1% configurable |
| Metriques | Total trades, win rate, P&L, max drawdown, Sharpe, Sortino, Calmar, profit factor |
| Graphique equity | Courbe d'equity avec drawdowns marques |
| Graphique trades | Bougies + markers BUY/SELL |
| Comparaison | Comparer 2 strategies cote a cote |
| Walk-forward | Optimise sur periode A, teste sur periode B |

### 2.4 Module : Dashboard

#### 2.4.1 Page Overview (Home)

| Composant | Donnees | Temps reel |
|-----------|---------|------------|
| Carte Prix | Prix actuel, variation 24h, sparkline | WebSocket |
| Carte Bot Status | Running/Stopped, uptime, mode, strategie active | 5s poll |
| Carte Position | Entry, qty, P&L non-realise, SL, TP, duree | WebSocket |
| Carte Compte | Solde USDT, BTC, valeur totale USD | WebSocket |
| KPI Cards | Total trades, win rate, P&L total, meilleur trade, pire trade, streak | 30s poll |
| Graphique Bougies | Bougies BTC avec indicateurs overlay | WebSocket |
| Equity Curve | Courbe P&L cumule (7/30/90 jours) | 5min poll |
| Trades Recents | 10 derniers trades avec P&L | 30s poll |
| Activite Multi-Paires | Liste des paires actives avec signaux | WebSocket |

#### 2.4.2 Page Trades

| Feature | Description |
|---------|-------------|
| Tableau complet | Tous les trades avec colonnes triables |
| Filtres | Par date, paire, strategie, statut, resultat |
| Recherche | Texte libre sur notes, raison d'entree |
| Export CSV | Telecharger l'historique |
| Detail trade | Panneau lateral avec tous les details + graphique |
| Journal | Ajout de notes, tags, captures d'ecran par trade |
| Statistiques inline | Win rate, P&L moyen, duree moyenne en bas du tableau |

#### 2.4.3 Page Strategy Builder

Voir section 2.3.

#### 2.4.4 Page Backtester

| Feature | Description |
|---------|-------------|
| Selection strategie | Dropdown ou creer une nouvelle |
| Periode | Date picker start/end |
| Paire | Selection de la paire |
| Capital initial | Montant de depart |
| Lancement | Bouton + barre de progression |
| Resultats | KPI cards + equity curve + liste des trades |
| Comparaison | Onglet pour comparer 2+ backtests |
| Historique | Liste des backtests passes |

#### 2.4.5 Page Portfolio

| Feature | Description |
|---------|-------------|
| Vue globale | Toutes les positions ouvertes sur toutes les paires |
| Allocation | Graphique camembert de l'allocation par paire |
| Exposure | % du capital engage, marge disponible |
| P&L agrege | P&L total non-realise + realise du jour |
| Correlation matrix | Heatmap des correlations entre paires actives |
| Risk metrics | Drawdown actuel, VaR, exposure par paire |

#### 2.4.6 Page Alertes

| Feature | Description |
|---------|-------------|
| Creer une alerte | Prix atteint X, RSI > Y, drawdown > Z |
| Canaux | Telegram, Push (mobile), Email |
| Historique | Liste des alertes declenchees |
| Alertes systeme | Bot down, erreur API, SL touche |
| Alertes strategie | Signal BUY/SELL genere, filtre bloque |

#### 2.4.7 Page Agent IA

| Feature | Description |
|---------|-------------|
| Configuration | Modele LLM, system prompt, permissions |
| Chat integre | Conversation avec l'agent IA directement dans le dashboard (pas que Telegram) |
| Rapports | Generation et historique des rapports |
| Suggestions | L'agent IA suggere des optimisations |

#### 2.4.8 Page Settings

| Feature | Description |
|---------|-------------|
| Profil | Nom, email, timezone, langue |
| Exchange | Cles API (masquees), test connexion |
| Trading | DRY-RUN/LIVE toggle, capital, risk limits |
| Notifications | Configuration Telegram, Push, Email |
| Apparence | Theme clair/sombre, couleurs des graphiques |
| API Keys | Gestion des cles API tierces |
| Securite | 2FA, sessions actives, changer mot de passe |
| Backup | Export/Import de toute la configuration |

#### 2.4.9 Page Logs

| Feature | Description |
|---------|-------------|
| Logs temps reel | Stream des logs du bot avec auto-scroll |
| Filtres | Par niveau (INFO, WARNING, ERROR), par module |
| Recherche | Texte libre dans les logs |
| Telechargement | Export des logs en fichier |

### 2.5 Module : Notifications

| Canal | Notifications |
|-------|--------------|
| **Telegram** | Tous les evenements (BUY, SELL, SL, erreurs, statut) |
| **Push Mobile** | BUY, SELL, SL touche, erreurs critiques |
| **Email** | Rapport journalier, alertes critiques |
| **In-App** | Badge + toast pour tous les evenements |
| **WebSocket** | Temps reel vers dashboard et mobile |

Format des notifications enrichi :

```
📈 KAIROS - BUY EXECUTE
━━━━━━━━━━━━━━━━
Paire: BTC/USDT
Prix: $67,234.50
Quantite: 0.00148 BTC
Capital: $99.50
Strategie: Scalping Hard
Raison: RSI bounce + MACD cross

Stop-Loss: $66,225.99 (-1.5%)
Trailing: +0.6% → 0.3%
━━━━━━━━━━━━━━━━
Solde: 136.50 USDT | Mode: LIVE
```

### 2.6 Module : Agent IA

#### 2.6.1 Canaux

| Canal | Fonctionnalite |
|-------|----------------|
| **Telegram** | Chat complet, commandes rapides |
| **Dashboard** | Chat integre dans l'interface web |
| **Mobile** | Chat dans l'app |

#### 2.6.2 Commandes

| Commande | Description |
|----------|-------------|
| `/status` | Etat complet (bot, positions, solde) |
| `/stats [jours]` | Statistiques sur N jours |
| `/portfolio` | Vue portfolio multi-paires |
| `/backtest <strategie> <jours>` | Lancer un backtest |
| `/compare <jours>` | Comparer toutes les strategies |
| `/optimize <param>` | Optimiser un parametre |
| `/alert <condition>` | Creer une alerte en langage naturel |
| `/report` | Generer un rapport IA |
| `/explain <trade_id>` | Expliquer un trade passe |
| `/suggest` | Suggestions d'amelioration |
| `/risk` | Analyse du risque actuel |
| `/help` | Aide |

#### 2.6.3 Outils IA (Function Calling)

| Outil | Mode | Description |
|-------|------|-------------|
| `get_bot_status` | Read | Etat du bot |
| `get_trade_history` | Read | Historique des trades |
| `get_trade_stats` | Read | Statistiques |
| `get_portfolio` | Read | Vue portfolio |
| `get_market_analysis` | Read | Analyse technique multi-TF |
| `list_strategies` | Read | Liste des strategies |
| `get_strategy_detail` | Read | Detail d'une strategie |
| `run_backtest` | Execute | Lancer un backtest |
| `get_alerts` | Read | Alertes actives |
| `create_alert` | Write | Creer une alerte |
| `get_correlation_matrix` | Read | Correlations entre paires |
| `get_risk_metrics` | Read | Metriques de risque |

**Securite** : Aucun outil ne peut executer de trade ou modifier une strategie active. Les outils Write sont limites aux alertes.

### 2.7 Module : Backtester

#### 2.7.1 Architecture

```
Historical Data (CSV/API) → Candle Replay Engine
                                    ↓
                            Core Trading Engine
                            (meme code que live)
                                    ↓
                            Trade Simulator
                            (frais + slippage)
                                    ↓
                            Metrics Calculator
                                    ↓
                            Report Generator
```

**Point cle** : Le backtester utilise **exactement le meme Core Engine** que le mode live. Zero divergence.

#### 2.7.2 Metriques

| Metrique | Description |
|----------|-------------|
| Total Trades | Nombre de trades executes |
| Win Rate | % de trades gagnants |
| P&L Total | Profit/perte total en USDT |
| P&L % | Rendement en pourcentage |
| Max Drawdown | Pire perte depuis un peak |
| Sharpe Ratio | Rendement ajuste au risque |
| Sortino Ratio | Sharpe mais penalise uniquement les pertes |
| Calmar Ratio | Rendement annualise / max drawdown |
| Profit Factor | Somme gains / somme pertes |
| Average Win | Gain moyen par trade gagnant |
| Average Loss | Perte moyenne par trade perdant |
| Risk/Reward | Ratio moyen gain/perte |
| Avg Duration | Duree moyenne d'un trade |
| Max Consecutive Wins | Plus longue serie gagnante |
| Max Consecutive Losses | Plus longue serie perdante |
| Expectancy | Gain moyen attendu par trade |

#### 2.7.3 Modes

| Mode | Description |
|------|-------------|
| Simple | Backtest sur une periode fixe |
| Walk-Forward | Optimise sur 70%, teste sur 30%, rolling |
| Monte Carlo | Simule 1000 scenarios en randomisant l'ordre des trades |
| Paper Trading | Backtest en temps reel sur donnees live (sans executer) |

---

## 3. Wireframes / UX-UI

### 3.1 Layout General

Template : **WowDash React TypeScript shadcn/ui** (identique au bot actuel).

```
┌──────────────────────────────────────────────────────────┐
│  [Logo] KAIROS TRADING          🔔 3   👤 Jalal   ☀/🌙  │
├────────────┬─────────────────────────────────────────────┤
│            │                                             │
│  SIDEBAR   │              MAIN CONTENT                   │
│            │                                             │
│  Overview  │  ┌─────────────────────────────────────┐    │
│  Portfolio │  │                                     │    │
│  Trades    │  │         Page content here            │    │
│  ─────     │  │                                     │    │
│  Strategy  │  │                                     │    │
│  Builder   │  │                                     │    │
│  Backtest  │  │                                     │    │
│  ─────     │  │                                     │    │
│  Alertes   │  │                                     │    │
│  Agent IA  │  └─────────────────────────────────────┘    │
│  Rapports  │                                             │
│  ─────     │                                             │
│  Logs      │                                             │
│  Settings  │                                             │
│            │                                             │
└────────────┴─────────────────────────────────────────────┘
```

### 3.2 Sidebar Navigation

```
KAIROS TRADING
━━━━━━━━━━━━━━━━━━━━

  TRADING
  ├── 📊 Overview
  ├── 💼 Portfolio
  └── 📋 Historique Trades

  STRATEGIES
  ├── 🎯 Strategy Builder
  └── 🧪 Backtester

  INTELLIGENCE
  ├── 🤖 Agent IA
  └── 📄 Rapports IA

  MONITORING
  ├── 🔔 Alertes
  └── 📜 Logs

  ───────────────

  ⚙️ Parametres
```

### 3.3 Page Overview (Dashboard)

```
┌────────────────────────────────────────────────────────┐
│  Overview                              Derniere MAJ: 2s │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ BTC/USDT │ │ Bot      │ │ Position │ │ Compte   │  │
│  │ $67,234  │ │ ● Active │ │ BTC Long │ │ 136 USDT │  │
│  │ +2.3%24h │ │ 14h23m   │ │ +0.45%   │ │ 0.002BTC │  │
│  │ ~~~~~~~~ │ │ Scalping │ │ SL:-1.5% │ │ $270 tot │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                        │
│  ┌────────────────────────┐ ┌────────────────────────┐ │
│  │ Graphique Bougies      │ │ KPIs                   │ │
│  │                        │ │                        │ │
│  │   📈 BTC/USDT 5m      │ │  Trades: 47            │ │
│  │                        │ │  Win Rate: 63%         │ │
│  │  ┃█┃█┃▌┃█┃█┃█┃▌┃█┃█  │ │  P&L: +$12.45         │ │
│  │  ┃▌┃█┃█┃▌┃▌┃█┃█┃█┃▌  │ │  Drawdown: -2.1%      │ │
│  │  ────BB────EMA────     │ │  Best: +$3.20          │ │
│  │                        │ │  Streak: 4W            │ │
│  │  [1m] [5m] [15m] [1h] │ │  Aujourd'hui: +$1.85  │ │
│  └────────────────────────┘ └────────────────────────┘ │
│                                                        │
│  ┌────────────────────────┐ ┌────────────────────────┐ │
│  │ Courbe d'Equity        │ │ Trades Recents         │ │
│  │                        │ │                        │ │
│  │      ╱──╲    ╱──       │ │  #47 BUY  +0.45% ●    │ │
│  │    ╱─    ╲╱╱─          │ │  #46 SELL -0.32% ○ SL │ │
│  │  ╱─                    │ │  #45 SELL +1.23% ●    │ │
│  │ ╱                      │ │  #44 SELL +0.67% ●    │ │
│  │ [7j] [30j] [90j] [All]│ │  #43 SELL -0.89% ○    │ │
│  └────────────────────────┘ └────────────────────────┘ │
│                                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Paires Actives                                  │   │
│  │                                                 │   │
│  │  BTC/USDT  $67,234  ● Long  +0.45%  Scalping   │   │
│  │  ETH/USDT  $2,456   ○ Idle  ---     RSI Bounce │   │
│  │  SOL/USDT  $124.50  ● Long  +1.2%   Momentum   │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

### 3.4 Page Portfolio

```
┌────────────────────────────────────────────────────────┐
│  Portfolio                                              │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Capital  │ │ Positions│ │ Exposure │ │ P&L Jour │  │
│  │ $270.50  │ │ 2 / 5    │ │ 67%      │ │ +$4.50   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                        │
│  POSITIONS OUVERTES                                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Paire     │ Cote │ Entry    │ Actuel   │ P&L    │   │
│  │───────────│──────│──────────│──────────│────────│   │
│  │ BTC/USDT  │ LONG │ $67,100  │ $67,234  │ +0.20% │   │
│  │           │      │ 0.001BTC │ SL:66225 │ +$0.13 │   │
│  │───────────│──────│──────────│──────────│────────│   │
│  │ SOL/USDT  │ LONG │ $123.40  │ $124.50  │ +0.89% │   │
│  │           │      │ 0.8 SOL  │ SL:121.5 │ +$0.88 │   │
│  └─────────────────────────────────────────────────┘   │
│                                                        │
│  ┌──────────────────────┐ ┌──────────────────────────┐ │
│  │ Allocation           │ │ Correlation Matrix       │ │
│  │                      │ │                          │ │
│  │    ┌────┐            │ │      BTC  ETH  SOL      │ │
│  │   ┌┤USDT├┐           │ │ BTC  1.0  0.8  0.6      │ │
│  │  ┌┤│ 33%│├┐          │ │ ETH  0.8  1.0  0.7      │ │
│  │  │BTC   SOL│         │ │ SOL  0.6  0.7  1.0      │ │
│  │  │ 40%  27%│         │ │                          │ │
│  └──────────────────────┘ └──────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

### 3.5 Page Strategy Builder

```
┌────────────────────────────────────────────────────────┐
│  Strategy Builder                                      │
├──────────┬─────────────────────────────────────────────┤
│          │                                             │
│ LISTE    │  ┌──────────────────────────────────────┐   │
│          │  │ Nom: [Scalping Hard        ]         │   │
│ ● Scalp. │  │ Description: [RSI + MACD momentum ]  │   │
│   Hard   │  │ Timeframe: [5m ▼]    Paire: [ALL ▼] │   │
│ ○ RSI    │  │ Status: ✅ Validee  ● Active         │   │
│   Bounce │  └──────────────────────────────────────┘   │
│ ○ MSB    │                                             │
│   Gliss. │  ┌──── CONDITIONS D'ENTREE ──── [AND] ──┐  │
│          │  │                                       │  │
│          │  │  ≡ [RSI ▼]  [< ▼]  [30]   ⚙ ✕      │  │
│ ─────    │  │  ≡ [MACD ▼] [hist_pos ▼]  ⚙ ✕      │  │
│ [+Nouv.] │  │  ≡ [Heikin Ashi ▼] [vert ▼] ✕      │  │
│ [Dupli.] │  │                                       │  │
│ [Suppr.] │  │  [+ Ajouter une condition]            │  │
│          │  └───────────────────────────────────────┘  │
│          │                                             │
│          │  ┌──── CONDITIONS DE SORTIE ──── [OR] ───┐  │
│          │  │                                       │  │
│          │  │  ≡ [RSI ▼]  [> ▼]  [75]   ⚙ ✕      │  │
│          │  │  ≡ [Heikin Ashi ▼] [rouge ▼]  ✕     │  │
│          │  │                                       │  │
│          │  │  [+ Ajouter une condition]            │  │
│          │  └───────────────────────────────────────┘  │
│          │                                             │
│          │  ┌──── FILTRES POST-SIGNAL ──────────────┐  │
│          │  │                                       │  │
│          │  │  📈 EMA Tendance    [ON]  P:50 TF:1h │  │
│          │  │  🕐 Heures Trading  [OFF] 8h-22h     │  │
│          │  │  ⏱  Cooldown Perte  [OFF] 30min      │  │
│          │  │  📊 Max Trades/Jour [ON]  5           │  │
│          │  │  📉 Max Perte/Jour  [OFF] 3%          │  │
│          │  │  🌊 Filtre Volatil. [OFF] ATR range   │  │
│          │  └───────────────────────────────────────┘  │
│          │                                             │
│          │  ┌──── RISK MANAGEMENT ──────────────────┐  │
│          │  │                                       │  │
│          │  │  Stop-Loss: ████████░░ 1.5%           │  │
│          │  │  Trailing:  [ON] Activ: 0.6% Dist:0.3 │  │
│          │  │  TP Partiel:[ON] 50% a +1.0%          │  │
│          │  │  Position:  ████████████ 100%          │  │
│          │  │  Max Trades: [5] /jour                │  │
│          │  └───────────────────────────────────────┘  │
│          │                                             │
│          │  ┌─────────────────────────────────────┐    │
│          │  │ [Valider] [Sauvegarder] │ [Backtest]│   │
│          │  │                         │ [Activer] │   │
│          │  └─────────────────────────────────────┘    │
└──────────┴─────────────────────────────────────────────┘
```

### 3.6 Page Backtester

```
┌────────────────────────────────────────────────────────┐
│  Backtester                                            │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──── CONFIGURATION ──────────────────────────────┐   │
│  │ Strategie: [Scalping Hard ▼]                    │   │
│  │ Paire: [BTC/USDT ▼]   Capital: [$100      ]    │   │
│  │ Du: [2026-01-01] Au: [2026-02-10]               │   │
│  │ Frais: [0.1%]  Slippage: [0.05%]               │   │
│  │                                                 │   │
│  │ [▶ Lancer le Backtest]  [▶ Walk-Forward]        │   │
│  └─────────────────────────────────────────────────┘   │
│                                                        │
│  ┌──── RESULTATS ──────────────────────────────────┐   │
│  │                                                 │   │
│  │ ┌────────┐┌────────┐┌────────┐┌────────┐       │   │
│  │ │Trades  ││Win Rate││P&L     ││Drawdown│       │   │
│  │ │  23    ││ 65.2%  ││+$8.45  ││ -3.2%  │       │   │
│  │ └────────┘└────────┘└────────┘└────────┘       │   │
│  │ ┌────────┐┌────────┐┌────────┐┌────────┐       │   │
│  │ │Sharpe  ││Sortino ││PF      ││Avg Win │       │   │
│  │ │ 1.45   ││ 2.10   ││ 1.82   ││ +0.65% │       │   │
│  │ └────────┘└────────┘└────────┘└────────┘       │   │
│  │                                                 │   │
│  │ ┌─── Equity Curve ─────────────────────────┐    │   │
│  │ │                                          │    │   │
│  │ │  $108 ─       ╱──╲    ╱──────           │    │   │
│  │ │  $104 ─    ╱╱─    ╲╱╱─                  │    │   │
│  │ │  $100 ─╱╱─                              │    │   │
│  │ │  $96  ─                                  │    │   │
│  │ │        Jan 10    Jan 20    Jan 30  Feb 10│    │   │
│  │ └─────────────────────────────────────────┘    │   │
│  │                                                 │   │
│  │ ┌─── Trades sur Graphique ─────────────────┐    │   │
│  │ │                                          │    │   │
│  │ │  🔼BUY   🔽SELL(+)   🔻SELL(-)          │    │   │
│  │ │  ┃█┃█🔼┃▌┃█🔽┃█┃▌┃█🔼┃█┃█🔽┃▌┃█       │    │   │
│  │ └─────────────────────────────────────────┘    │   │
│  │                                                 │   │
│  │ ┌─── Liste des Trades ─────────────────────┐    │   │
│  │ │ #  │ Entry    │ Exit     │ P&L   │ Duree │    │   │
│  │ │ 1  │ $67,100  │ $67,500  │+0.60% │ 25min │    │   │
│  │ │ 2  │ $67,400  │ $67,200  │-0.30% │ 12min │    │   │
│  │ │ .. │ ...      │ ...      │ ...   │ ...   │    │   │
│  │ └─────────────────────────────────────────┘    │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
```

### 3.7 Page Agent IA (Chat Integre)

```
┌────────────────────────────────────────────────────────┐
│  Agent IA                     [⚙ Config] [📊 Rapports] │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──── CHAT ───────────────────────────────────────┐   │
│  │                                                 │   │
│  │  🤖 Bonjour ! Je suis Kairos, votre assistant   │   │
│  │     de trading. Comment puis-je vous aider ?    │   │
│  │                                                 │   │
│  │  👤 Quel est le statut du bot ?                 │   │
│  │                                                 │   │
│  │  🤖 Voici l'etat actuel :                      │   │
│  │     ● Bot actif depuis 14h23m                   │   │
│  │     ● Strategie: Scalping Hard                  │   │
│  │     ● Position: BTC LONG +0.45%                 │   │
│  │     ● Solde: 136.50 USDT                       │   │
│  │     ● Trades aujourd'hui: 3 (2W/1L)            │   │
│  │                                                 │   │
│  │  👤 Compare les strategies sur 30 jours         │   │
│  │                                                 │   │
│  │  🤖 Je lance la comparaison...                  │   │
│  │     ┌────────────┬────────┬───────┐             │   │
│  │     │ Strategie  │Win Rate│ P&L   │             │   │
│  │     │ Scalping   │ 63%   │+$12.4 │             │   │
│  │     │ RSI Bounce │ 58%   │ +$8.2 │             │   │
│  │     │ MSB Gliss. │ 67%   │+$15.1 │             │   │
│  │     └────────────┴────────┴───────┘             │   │
│  │                                                 │   │
│  ├─────────────────────────────────────────────────┤   │
│  │  [Message...]                        [Envoyer]  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                        │
│  RACCOURCIS : /status /stats /portfolio /risk /suggest  │
└────────────────────────────────────────────────────────┘
```

### 3.8 Page Settings

```
┌────────────────────────────────────────────────────────┐
│  Parametres                                            │
├──────────┬─────────────────────────────────────────────┤
│          │                                             │
│ Sections │  ┌──── TRADING ─────────────────────────┐   │
│          │  │                                      │   │
│ ● Trading│  │  Mode: [DRY-RUN ○] [● LIVE]         │   │
│ ○ Exchange│  │  ⚠ Attention: LIVE = argent reel    │   │
│ ○ Notifs │  │                                      │   │
│ ○ Agent  │  │  Capital: [Tout le solde ●]          │   │
│ ○ Apparen│  │           [Montant fixe ○] [$100  ]  │   │
│ ○ Securit│  │                                      │   │
│ ○ Backup │  │  ── Risk Limits ──                   │   │
│          │  │  Max positions:    [3    ▼]          │   │
│          │  │  Max exposure:     ████████░░ 80%    │   │
│          │  │  Max drawdown/j:   ████░░░░░░ 5%    │   │
│          │  │  Max drawdown tot: ████████░░ 15%    │   │
│          │  │                                      │   │
│          │  │  ── Paires Actives ──                │   │
│          │  │  [✅] BTC/USDT                       │   │
│          │  │  [✅] ETH/USDT                       │   │
│          │  │  [  ] SOL/USDT                       │   │
│          │  │  [  ] BNB/USDT                       │   │
│          │  │  [+ Ajouter une paire]               │   │
│          │  │                                      │   │
│          │  │ [Sauvegarder]                        │   │
│          │  └──────────────────────────────────────┘   │
└──────────┴─────────────────────────────────────────────┘
```

### 3.9 Composants Mobile (React Native)

```
┌─────────────────────┐    ┌─────────────────────┐
│ KAIROS    ☰    🔔 3 │    │ ← Trade #47         │
├─────────────────────┤    ├─────────────────────┤
│                     │    │                     │
│  BTC/USDT           │    │  BTC/USDT           │
│  $67,234.50  +2.3%  │    │  BUY @ $67,100      │
│  ~~~~~~~~ sparkline │    │  SELL @ $67,500      │
│                     │    │  P&L: +$0.40 (+0.6%)│
│ ┌─────┐ ┌─────┐    │    │                     │
│ │● Bot│ │ P&L │    │    │  ┌─────────────────┐│
│ │Actif│ │+$12 │    │    │  │ Graphique bougie ││
│ └─────┘ └─────┘    │    │  │ avec entry/exit  ││
│                     │    │  │ markers          ││
│ POSITION OUVERTE    │    │  └─────────────────┘│
│ ┌─────────────────┐ │    │                     │
│ │ BTC LONG +0.45% │ │    │  Strategie: Scalp.  │
│ │ Entry: $67,100  │ │    │  Raison: RSI bounce │
│ │ SL: $66,225     │ │    │  Duree: 25 min      │
│ │ P&L: +$0.30     │ │    │  Frais: $0.04       │
│ └─────────────────┘ │    │                     │
│                     │    │  --- Notes ---       │
│ TRADES RECENTS      │    │  [Ajouter une note] │
│ #47 BUY  +0.45% ●  │    │                     │
│ #46 SELL -0.32% ○  │    └─────────────────────┘
│ #45 SELL +1.23% ●  │
│                     │
├─────────────────────┤
│ 📊  💼  🎯  🤖  ⚙ │
│ Home Port Strat AI  Set│
└─────────────────────┘
```

---

## 4. Architecture Technique

### 4.1 Vue d'Ensemble

```
                        INTERNET
                           │
                  ┌────────┴────────┐
                  │    Traefik      │
                  │  (SSL + Proxy)  │
                  └────────┬────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────┴──────┐  ┌─────┴──────┐  ┌──────┴──────┐
   │ Web Frontend │  │ Mobile App │  │  Authelia   │
   │ (Nginx+React)│  │(RN / Expo) │  │   (Auth)    │
   └──────┬──────┘  └─────┬──────┘  └─────────────┘
          │                │
          └───────┬────────┘
                  │ REST + WebSocket
          ┌───────┴───────┐
          │   API Gateway │
          │  (FastAPI)    │
          │  Port 8000    │
          └───┬───┬───┬───┘
              │   │   │
     ┌────────┘   │   └────────┐
     │            │            │
┌────┴────┐ ┌────┴────┐ ┌─────┴─────┐
│ Trading │ │   AI    │ │ Notifier  │
│ Engine  │ │  Agent  │ │ Service   │
│ (Core)  │ │(OpenR.) │ │(Tg/Push)  │
└────┬────┘ └────┬────┘ └───────────┘
     │           │
┌────┴────┐ ┌───┴────┐
│ Market  │ │PostgreSQL│
│ Gateway │ │   DB    │
│(Binance)│ └─────────┘
│  WS+REST│
└─────────┘
```

### 4.2 Containers Docker (7)

| Container | Image | Role | Port | Depends |
|-----------|-------|------|------|---------|
| `kairos-frontend` | Nginx + React build | Dashboard web | 80 | api |
| `kairos-api` | FastAPI | API REST + WebSocket | 8000 | db |
| `kairos-engine` | Python | Trading engine 24/7 | - | api, db |
| `kairos-ai-agent` | Python | Agent IA Telegram + tools | - | api |
| `kairos-notifier` | Python | Service de notifications | - | db |
| `kairos-db` | PostgreSQL 16 | Base de donnees | 5432 | - |
| `kairos-redis` | Redis 7 | Cache + pub/sub + rate limit | 6379 | - |

### 4.3 Architecture du Trading Engine

```python
# Principe : Le Core n'a AUCUNE dependance I/O

# ─── CORE (pur Python, testable) ─────────────────
core/
├── models.py              # Candle, Signal, Position, Trade (dataclasses)
├── indicators/
│   ├── registry.py        # IndicatorRegistry (decouvre auto les indicateurs)
│   ├── base.py            # BaseIndicator (interface commune)
│   ├── ema.py             # EMA (incremental)
│   ├── rsi.py             # RSI (incremental)
│   ├── macd.py            # MACD
│   ├── bollinger.py       # Bollinger Bands
│   ├── heikin_ashi.py     # Heikin Ashi
│   ├── msb.py             # MSB Glissant (stateful)
│   ├── supertrend.py      # Supertrend
│   ├── ichimoku.py        # Ichimoku (NOUVEAU)
│   ├── order_block.py     # Order Block (NOUVEAU)
│   └── ...                # 25 indicateurs au total
├── strategy/
│   ├── evaluator.py       # Evalue les conditions JSON (recursif)
│   ├── filters.py         # Post-signal filters
│   └── loader.py          # Charge et valide les strategies JSON
├── risk/
│   ├── position.py        # Stop-loss, trailing, partial TP, break-even
│   ├── portfolio.py       # Exposure, max drawdown, correlation
│   └── sizing.py          # Position sizing (fixed, % equity, Kelly)
└── timeframe/
    ├── aggregator.py      # Aggrege 1m → 3m → 5m → 15m → ...
    └── buffer.py          # Buffer circulaire par TF

# ─── ADAPTERS (I/O) ──────────────────────────────
adapters/
├── exchanges/
│   ├── base.py            # BaseExchange (interface)
│   ├── binance_ws.py      # Binance WebSocket streams
│   ├── binance_rest.py    # Binance REST (ordres, solde)
│   └── bybit.py           # Bybit (futur)
├── database/
│   ├── repository.py      # TradeRepository, StrategyRepository
│   └── models.py          # SQLAlchemy models
├── notifications/
│   ├── telegram.py        # Telegram Bot API
│   ├── push.py            # Firebase Cloud Messaging
│   └── email.py           # SMTP
└── cache/
    └── redis.py           # Cache prix, rate limiting

# ─── MODES (orchestration) ────────────────────────
modes/
├── live.py                # Orchestre core + adapters en live
├── backtest.py            # Replay historique avec le meme core
├── paper.py               # Simule ordres sur donnees live
└── optimize.py            # Grid search / walk-forward
```

### 4.4 Flux de Donnees Event-Driven

```
Binance WebSocket
  │
  ├── kline_1m (OHLCV) ──────────────────┐
  ├── bookTicker (bid/ask) ───────┐       │
  └── userData (fills, balance) ──┤       │
                                  │       │
                          ┌───────┴───────┴────────┐
                          │   Market Gateway        │
                          │   (asyncio)             │
                          │                         │
                          │  1. Valide la bougie    │
                          │  2. Publie sur Redis    │
                          │  3. Callback engine     │
                          └───────────┬─────────────┘
                                      │
                              ┌───────┴───────┐
                              │ Trading Engine │
                              │               │
                              │ on_candle():   │
                              │  1. Update TF  │
                              │  2. Update ind.│
                              │  3. Eval strat.│
                              │  4. Check risk │
                              │  5. → Signal?  │
                              └───────┬───────┘
                                      │
                          ┌───────────┴───────────┐
                          │    Si Signal BUY/SELL  │
                          ├────────────────────────┤
                          │                        │
                   ┌──────┴──────┐          ┌──────┴──────┐
                   │ Adapter     │          │ Adapter     │
                   │ Exchange    │          │ Notifier    │
                   │ (exec ordre)│          │ (Tg + Push) │
                   └──────┬──────┘          └─────────────┘
                          │
                   ┌──────┴──────┐
                   │ Adapter DB  │
                   │ (save trade)│
                   └─────────────┘
```

### 4.5 Communication Inter-Services

| De | Vers | Protocole | Usage |
|----|------|-----------|-------|
| Engine → API | HTTP REST | Enregistrer trades, lire strategies |
| Engine → Redis | Redis Pub/Sub | Publier prix, signaux, etat |
| API → Redis | Redis Sub | Recevoir updates temps reel |
| API → Frontend | WebSocket | Push prix, positions, alertes |
| API → Mobile | WebSocket + Push | Push prix, positions, alertes |
| AI Agent → API | HTTP REST | Lire donnees (read-only) |
| Notifier → Redis | Redis Sub | Recevoir evenements a notifier |
| Notifier → Telegram | Telegram API | Envoyer messages |
| Notifier → Firebase | FCM | Push notifications mobile |

### 4.6 Stack Technologique

| Couche | Technologie |
|--------|-------------|
| **Frontend Web** | React 18 + TypeScript + Tailwind + shadcn/ui (WowDash) |
| **Frontend Mobile** | React Native + Expo + NativeWind |
| **API** | FastAPI (Python 3.12) + Pydantic v2 |
| **Trading Engine** | Python 3.12 (asyncio) |
| **AI Agent** | Python + OpenRouter + function calling |
| **Base de donnees** | PostgreSQL 16 |
| **Cache / Pub-Sub** | Redis 7 |
| **ORM** | SQLAlchemy 2.0 + Alembic (migrations) |
| **Auth** | JWT (access + refresh tokens) + API keys |
| **Reverse Proxy** | Traefik v3 |
| **Conteneurisation** | Docker + Docker Compose |
| **CI/CD** | GitHub Actions |
| **Monitoring** | Prometheus + Grafana (optionnel phase 2) |
| **Logging** | structlog (JSON) + Loki (optionnel) |

---

## 5. Schema de Base de Donnees

### 5.1 Diagramme ERD

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│   users     │     │    trades       │     │  strategies  │
├─────────────┤     ├─────────────────┤     ├──────────────┤
│ id (PK)     │◄────│ user_id (FK)    │  ┌──│ id (PK)      │
│ email       │     │ id (PK)         │  │  │ user_id (FK) │
│ password    │     │ strategy_id(FK) │──┘  │ name         │
│ username    │     │ pair_id (FK)    │──┐  │ version      │
│ timezone    │     │ exchange        │  │  │ json_def     │
│ created_at  │     │ side            │  │  │ is_active    │
│ settings    │     │ entry_price     │  │  │ is_validated │
└──────┬──────┘     │ exit_price      │  │  │ stats        │
       │            │ quantity         │  │  │ created_at   │
       │            │ pnl             │  │  │ updated_at   │
       │            │ pnl_pct         │  │  └──────────────┘
       │            │ status          │  │
       │            │ entry_reason    │  │  ┌──────────────┐
       │            │ exit_reason     │  │  │   pairs      │
       │            │ entry_time      │  │  ├──────────────┤
       │            │ exit_time       │  └──│ id (PK)      │
       │            │ fees            │     │ symbol       │
       │            │ is_dry_run      │     │ base_asset   │
       │            │ notes           │     │ quote_asset  │
       │            │ tags            │     │ exchange     │
       │            └─────────────────┘     │ is_active    │
       │                                    │ min_qty      │
       │            ┌─────────────────┐     │ step_size    │
       │            │   alerts        │     └──────────────┘
       │            ├─────────────────┤
       ├────────────│ user_id (FK)    │     ┌──────────────┐
       │            │ id (PK)         │     │ daily_stats  │
       │            │ name            │     ├──────────────┤
       │            │ condition       │     │ id (PK)      │
       │            │ channels        │     │ user_id (FK) │
       │            │ is_active       │     │ pair_id (FK) │
       │            │ triggered_at    │     │ date         │
       │            │ created_at      │     │ trades       │
       │            └─────────────────┘     │ wins/losses  │
       │                                    │ pnl          │
       │            ┌─────────────────┐     │ best/worst   │
       │            │  ai_reports     │     └──────────────┘
       │            ├─────────────────┤
       └────────────│ user_id (FK)    │     ┌──────────────┐
                    │ id (PK)         │     │  backtests   │
                    │ report_type     │     ├──────────────┤
                    │ status          │     │ id (PK)      │
                    │ content         │     │ strategy_id  │
                    │ metrics         │     │ pair_id      │
                    │ created_at      │     │ start_date   │
                    └─────────────────┘     │ end_date     │
                                            │ capital      │
                    ┌─────────────────┐     │ metrics      │
                    │ trade_journal   │     │ trades_json  │
                    ├─────────────────┤     │ created_at   │
                    │ id (PK)         │     └──────────────┘
                    │ trade_id (FK)   │
                    │ note            │     ┌──────────────┐
                    │ tags            │     │ notifications│
                    │ screenshot_url  │     ├──────────────┤
                    │ created_at      │     │ id (PK)      │
                    └─────────────────┘     │ user_id (FK) │
                                            │ type         │
                                            │ channel      │
                                            │ content      │
                                            │ sent_at      │
                                            │ read_at      │
                                            └──────────────┘
```

### 5.2 Tables Detaillees

#### users

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    password    VARCHAR(255) NOT NULL,  -- bcrypt hash
    username    VARCHAR(50) NOT NULL,
    timezone    VARCHAR(50) DEFAULT 'UTC',
    language    VARCHAR(5) DEFAULT 'fr',
    settings    JSONB DEFAULT '{}',     -- preferences UI, theme, etc.
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ,
    last_login  TIMESTAMPTZ
);
```

#### trades

```sql
CREATE TABLE trades (
    id              SERIAL PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    strategy_id     UUID REFERENCES strategies(id),
    pair_id         INTEGER REFERENCES pairs(id),
    exchange        VARCHAR(20) DEFAULT 'binance',
    side            VARCHAR(4) NOT NULL,        -- 'BUY'
    entry_price     DECIMAL(20,8) NOT NULL,
    exit_price      DECIMAL(20,8),
    quantity        DECIMAL(20,8) NOT NULL,
    quote_quantity  DECIMAL(20,8),              -- montant USDT
    pnl             DECIMAL(20,8),
    pnl_pct         DECIMAL(10,4),
    fees_entry      DECIMAL(20,8) DEFAULT 0,
    fees_exit       DECIMAL(20,8) DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'OPEN', -- OPEN, CLOSED, CANCELLED
    entry_reason    VARCHAR(200),
    exit_reason     VARCHAR(100),
    entry_time      TIMESTAMPTZ NOT NULL,
    exit_time       TIMESTAMPTZ,
    is_dry_run      BOOLEAN DEFAULT TRUE,
    notes           TEXT,
    tags            TEXT[],                     -- array de tags
    metadata        JSONB DEFAULT '{}',         -- donnees supplementaires
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trades_user_status ON trades(user_id, status);
CREATE INDEX idx_trades_entry_time ON trades(entry_time DESC);
CREATE INDEX idx_trades_pair ON trades(pair_id);
```

#### strategies

```sql
CREATE TABLE strategies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    name            VARCHAR(100) NOT NULL,
    version         VARCHAR(10) DEFAULT '1.0',
    description     TEXT,
    json_definition JSONB NOT NULL,
    pair_id         INTEGER REFERENCES pairs(id),  -- NULL = toutes les paires
    is_active       BOOLEAN DEFAULT FALSE,
    is_validated    BOOLEAN DEFAULT FALSE,
    created_by      VARCHAR(50) DEFAULT 'user',
    total_trades    INTEGER DEFAULT 0,
    winning_trades  INTEGER DEFAULT 0,
    total_pnl       DECIMAL(20,8) DEFAULT 0,
    backtest_result JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ,
    UNIQUE(user_id, name)
);
```

#### pairs

```sql
CREATE TABLE pairs (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(20) UNIQUE NOT NULL,   -- 'BTCUSDT'
    base_asset  VARCHAR(10) NOT NULL,          -- 'BTC'
    quote_asset VARCHAR(10) NOT NULL,          -- 'USDT'
    exchange    VARCHAR(20) DEFAULT 'binance',
    is_active   BOOLEAN DEFAULT FALSE,
    min_qty     DECIMAL(20,8),
    step_size   DECIMAL(20,8),
    min_notional DECIMAL(20,8),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. Contrats API

### 6.1 Authentification

```
POST /api/auth/register    - Creer un compte
POST /api/auth/login       - Login → access_token + refresh_token
POST /api/auth/refresh     - Renouveler le token
POST /api/auth/logout      - Invalider le token
GET  /api/auth/me          - Profil utilisateur
PUT  /api/auth/me          - Modifier profil

Headers:
  Authorization: Bearer <access_token>
  x-internal-token: <token>  (pour communication inter-containers)
```

### 6.2 Trading

```
GET  /api/trades                    - Liste (pagination, filtres)
GET  /api/trades/{id}               - Detail d'un trade
GET  /api/trades/open               - Positions ouvertes
GET  /api/trades/stats              - Statistiques globales
GET  /api/trades/stats/daily        - Stats journalieres
GET  /api/trades/stats/by-strategy  - Stats par strategie
GET  /api/trades/stats/by-pair      - Stats par paire
POST /api/trades                    - Ouvrir un trade (interne)
PUT  /api/trades/{id}/close         - Fermer un trade (interne)
POST /api/trades/{id}/journal       - Ajouter note/tag
GET  /api/trades/export/csv         - Export CSV
```

### 6.3 Strategies

```
GET    /api/strategies              - Liste des strategies
GET    /api/strategies/{id}         - Detail
GET    /api/strategies/active       - Strategie(s) active(s)
GET    /api/strategies/indicators   - Liste des indicateurs
POST   /api/strategies              - Creer
PUT    /api/strategies/{id}         - Modifier
DELETE /api/strategies/{id}         - Supprimer
POST   /api/strategies/{id}/activate    - Activer
POST   /api/strategies/{id}/deactivate  - Desactiver
POST   /api/strategies/{id}/validate    - Valider
POST   /api/strategies/{id}/duplicate   - Dupliquer
POST   /api/strategies/{id}/export      - Export JSON
POST   /api/strategies/import           - Import JSON
```

### 6.4 Backtester

```
POST /api/backtest                  - Lancer un backtest
GET  /api/backtest/{id}             - Resultat
GET  /api/backtest/{id}/trades      - Trades du backtest
GET  /api/backtest/history          - Historique des backtests
POST /api/backtest/compare          - Comparer N backtests
DELETE /api/backtest/{id}           - Supprimer
```

### 6.5 Market

```
GET /api/market/price/{symbol}      - Prix actuel
GET /api/market/candles/{symbol}    - Bougies historiques
GET /api/market/balance             - Soldes
GET /api/market/pairs               - Paires disponibles
GET /api/market/connection-test     - Test exchange
```

### 6.6 Portfolio

```
GET /api/portfolio                  - Vue d'ensemble
GET /api/portfolio/positions        - Positions ouvertes
GET /api/portfolio/allocation       - Allocation par paire
GET /api/portfolio/risk             - Metriques de risque
GET /api/portfolio/correlation      - Matrice de correlation
GET /api/portfolio/equity-curve     - Courbe d'equity
```

### 6.7 Alertes

```
GET    /api/alerts                  - Liste des alertes
POST   /api/alerts                  - Creer une alerte
PUT    /api/alerts/{id}             - Modifier
DELETE /api/alerts/{id}             - Supprimer
GET    /api/alerts/history          - Alertes declenchees
POST   /api/alerts/{id}/test       - Tester une alerte
```

### 6.8 Notifications

```
GET  /api/notifications             - Notifications non-lues
PUT  /api/notifications/{id}/read   - Marquer comme lue
PUT  /api/notifications/read-all    - Tout marquer comme lu
GET  /api/notifications/config      - Config des canaux
PUT  /api/notifications/config      - Modifier config
POST /api/notifications/test/{channel} - Tester un canal
```

### 6.9 Agent IA

```
GET  /api/ai/config                 - Configuration
PUT  /api/ai/config                 - Modifier
GET  /api/ai/status                 - Etat
POST /api/ai/chat                   - Envoyer message (chat web)
GET  /api/ai/chat/history           - Historique des conversations
POST /api/ai/reports/generate       - Generer un rapport
GET  /api/ai/reports                - Liste des rapports
GET  /api/ai/reports/{id}           - Detail d'un rapport
DELETE /api/ai/reports/{id}         - Supprimer
```

### 6.10 Bot Control

```
GET  /api/bot/status                - Etat du bot
POST /api/bot/control               - Start/Stop/Restart
GET  /api/bot/config                - Configuration trading
PUT  /api/bot/config                - Modifier config
GET  /api/bot/logs                  - Derniers logs
GET  /api/bot/health                - Health check
```

### 6.11 WebSocket

```
WS /ws/market     - Prix temps reel, bougies (par paire)
WS /ws/trading    - Signaux, positions, trades (authentifie)
WS /ws/logs       - Stream des logs du bot
WS /ws/ai-chat    - Chat temps reel avec l'agent IA
```

---

## 7. Strategie Mobile

### 7.1 Architecture Mobile

```
React Native + Expo
├── Navigation (React Navigation)
│   ├── Tab: Overview
│   ├── Tab: Portfolio
│   ├── Tab: Strategies
│   ├── Tab: AI Agent
│   └── Tab: Settings
├── State: Zustand (leger, pas Redux)
├── API: axios + React Query (cache + retry)
├── WebSocket: socket.io-client
├── Push: Expo Notifications + Firebase
├── Charts: react-native-wagmi-charts
├── Storage: MMKV (cache local rapide)
└── Auth: Secure storage pour JWT
```

### 7.2 Notifications Push

| Evenement | Priorite | Son |
|-----------|----------|-----|
| BUY execute | Haute | Oui |
| SELL execute | Haute | Oui |
| Stop-loss touche | Haute | Oui |
| Trailing active | Normale | Non |
| Alerte declenchee | Haute | Oui |
| Bot erreur/crash | Critique | Oui |
| Rapport IA pret | Basse | Non |
| Drawdown max atteint | Critique | Oui |

### 7.3 Mode Offline

| Donnee | Cache Local | Duree |
|--------|-------------|-------|
| Dernier prix | MMKV | 5 min |
| Positions ouvertes | MMKV | 1 min |
| Historique trades | SQLite local | 24h |
| Stats | MMKV | 15 min |
| Strategies | MMKV | 1h |

### 7.4 API Mobile-Friendly

- Reponses paginées avec curseurs (pas d'offset)
- Compression gzip sur toutes les reponses
- ETags pour le cache HTTP
- Rate limiting par API key
- Endpoints agreges pour reduire les appels (ex: `/api/dashboard` = tout en 1)

---

## 8. Securite

### 8.1 Authentification

| Mesure | Implementation |
|--------|----------------|
| Passwords | bcrypt (cost 12) |
| JWT Access Token | Expire 15 min, signe HS256 |
| JWT Refresh Token | Expire 7 jours, rotation |
| 2FA | TOTP (Google Authenticator) - optionnel |
| API Keys | Pour l'acces programmatique (mobile) |
| Sessions | Liste des sessions actives, revocation |
| Brute force | Rate limit login : 5 tentatives / 15 min |

### 8.2 Donnees Sensibles

| Donnee | Stockage |
|--------|----------|
| Cles API Binance | Chiffrees en DB (AES-256-GCM) |
| Tokens Telegram | Chiffres en DB |
| JWT Secret | Variable d'environnement |
| Mot de passe DB | Variable d'environnement |
| Cle OpenRouter | Chiffree en DB |

### 8.3 Reseau

| Mesure | Implementation |
|--------|----------------|
| HTTPS | Let's Encrypt via Traefik (force) |
| CORS | Domaines explicites uniquement |
| CSP | Content Security Policy strict |
| Rate Limiting | Redis-backed, par IP + par user |
| Authelia | SSO pour l'acces web (optionnel) |
| Docker Network | Reseau interne isole |

### 8.4 Trading

| Mesure | Description |
|--------|-------------|
| DRY-RUN par defaut | Jamais de trading reel sans activation explicite |
| Confirmation LIVE | Double confirmation pour activer le mode live |
| Max exposure | Limite portfolio-level non-contournable |
| Max drawdown | Kill switch automatique |
| SL serveur exchange | Protection crash (SL place cote Binance) |
| Lock file | Empeche plusieurs instances du bot |
| Agent IA read-only | Aucune action de trading |
| Validation stricte | Bornes sur tous les parametres de risque |
| Audit log | Toute action est loguee avec timestamp et user |

---

## 9. Testing et Qualite

### 9.1 Strategie de Tests

| Type | Outil | Couverture Cible |
|------|-------|-----------------|
| Unit tests Core | pytest | 90%+ (indicateurs, evaluateur, risk) |
| Unit tests API | pytest + httpx | 80%+ (endpoints, validations) |
| Integration tests | pytest + testcontainers | DB, Redis, WebSocket |
| E2E tests | Playwright | Pages principales du dashboard |
| Mobile tests | Detox (optionnel) | Flows critiques |
| Load tests | Locust | API sous charge |

### 9.2 Tests Prioritaires

```
tests/
├── core/
│   ├── test_indicators/
│   │   ├── test_ema.py          # Valeurs connues vs Excel
│   │   ├── test_rsi.py
│   │   ├── test_macd.py
│   │   └── test_msb.py          # Scenarios stateful
│   ├── test_evaluator.py        # AND/OR/NOT, toutes combinaisons
│   ├── test_filters.py          # Chaque filtre independamment
│   ├── test_position.py         # SL, trailing, TP, break-even
│   ├── test_portfolio_risk.py   # Exposure, drawdown, correlation
│   └── test_aggregator.py       # 1m → 5m → 15m → ...
├── api/
│   ├── test_auth.py             # Register, login, refresh, 2FA
│   ├── test_trades.py           # CRUD, open/close flow
│   ├── test_strategies.py       # CRUD, validate, activate
│   └── test_backtest.py         # Lancement + resultats
├── integration/
│   ├── test_engine_flow.py      # Candle → signal → trade
│   ├── test_ws_stream.py        # WebSocket events
│   └── test_notification.py     # Telegram mock
└── e2e/
    ├── test_dashboard.py        # Chargement, donnees affichees
    ├── test_strategy_builder.py # Creer, editer, activer
    └── test_backtest_page.py    # Lancer, voir resultats
```

### 9.3 CI/CD Pipeline

```yaml
# .github/workflows/ci.yml
name: Kairos CI/CD

on: [push, pull_request]

jobs:
  lint:
    - ruff check .
    - mypy core/

  test:
    - pytest tests/core/ -v --cov=core --cov-report=xml
    - pytest tests/api/ -v
    - pytest tests/integration/ -v (avec PostgreSQL + Redis testcontainers)

  build:
    - docker build -t kairos-engine .
    - docker build -t kairos-api .
    - docker build -t kairos-frontend .

  deploy (main branch only):
    - scp vers VPS
    - docker compose down
    - docker compose build --no-cache
    - docker compose up -d
    - health check
    - rollback si echec
```

---

## 10. Infrastructure et DevOps

### 10.1 Docker Compose Production

```yaml
services:
  kairos-db:
    image: postgres:16-alpine
    volumes:
      - kairos_db_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: kairos
      POSTGRES_USER: kairos
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: pg_isready -U kairos

  kairos-redis:
    image: redis:7-alpine
    volumes:
      - kairos_redis_data:/data

  kairos-api:
    build: ./api
    depends_on: [kairos-db, kairos-redis]
    environment:
      DATABASE_URL: postgresql://kairos:${DB_PASSWORD}@kairos-db/kairos
      REDIS_URL: redis://kairos-redis:6379
      JWT_SECRET: ${JWT_SECRET}
    labels:
      - traefik.http.routers.kairos-api.rule=Host(`kairos.prozentia.com`) && PathPrefix(`/api`)

  kairos-engine:
    build: ./engine
    depends_on: [kairos-api, kairos-redis]
    volumes:
      - kairos_config:/app/config
      - kairos_logs:/app/logs

  kairos-ai-agent:
    build: ./ai-agent
    depends_on: [kairos-api]

  kairos-notifier:
    build: ./notifier
    depends_on: [kairos-redis]

  kairos-frontend:
    build: ./frontend
    labels:
      - traefik.http.routers.kairos.rule=Host(`kairos.prozentia.com`)
```

### 10.2 Monitoring

| Metrique | Source | Alerte |
|----------|--------|--------|
| CPU/RAM containers | Docker stats | > 80% |
| Trades/heure | PostgreSQL | 0 pendant 4h |
| Erreurs/min | Logs (structlog) | > 5/min |
| Latence API | FastAPI middleware | > 500ms p95 |
| WebSocket connexions | Redis | Deconnexion |
| DB connexions | PostgreSQL | > 80% pool |
| Drawdown | Engine | > max configurable |
| Espace disque | Host | > 90% |

### 10.3 Backup

| Donnee | Frequence | Retention | Destination |
|--------|-----------|-----------|-------------|
| PostgreSQL (pg_dump) | Toutes les 6h | 30 jours | S3 / local |
| Config JSON | A chaque modification | 90 jours | Git |
| Strategies | A chaque modification | Illimite | DB + export |
| Logs | Rotation quotidienne | 30 jours | Volume Docker |

---

## 11. Migration depuis BTC Sniper Bot

### 11.1 Donnees a Migrer

| Donnee | Source | Destination | Methode |
|--------|--------|-------------|---------|
| Trades historiques | SQLite `bot_panel.db` | PostgreSQL `trades` | Script Python |
| Strategies JSON | SQLite `strategies` | PostgreSQL `strategies` | Script Python |
| Configuration | `bot_config.json` | PostgreSQL `users.settings` + config | Script |
| Daily Stats | SQLite `daily_stats` | PostgreSQL `daily_stats` | Script |
| AI Reports | SQLite `ai_reports` | PostgreSQL `ai_reports` | Script |

### 11.2 Compatibilite

| Element | Compatibilite |
|---------|---------------|
| Format strategies JSON | 100% compatible (meme schema) |
| Cles API Binance | Reutilisables |
| Token Telegram | Reutilisable |
| Cle OpenRouter | Reutilisable |
| Domaine btcbot.prozentia.com | Migre vers kairos.prozentia.com |
| VPS Contabo | Meme serveur |

### 11.3 Plan de Migration

```
Phase 0 : BTC Sniper Bot continue de tourner
Phase 1 : Deployer Kairos sur le meme VPS (port different)
Phase 2 : Migrer les donnees (script automatique)
Phase 3 : Tester Kairos en DRY-RUN pendant 48h
Phase 4 : Basculer le DNS vers Kairos
Phase 5 : Arreter BTC Sniper Bot
Phase 6 : Activer Kairos en LIVE
```

---

## Annexe A : Nomenclature des Fichiers

```
kairos-trading/
├── README.md
├── CLAUDE.md
├── docker-compose.yml
├── docker-compose.prod.yml
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── core/                          # Pure Python, zero I/O
│   ├── __init__.py
│   ├── models.py                  # Candle, Signal, Position, Trade
│   ├── indicators/                # 25 indicateurs incrementaux
│   ├── strategy/                  # Evaluateur JSON + filtres
│   ├── risk/                      # Position + Portfolio risk
│   └── timeframe/                 # Aggregation + buffer
│
├── engine/                        # Trading engine (async)
│   ├── __init__.py
│   ├── main.py                    # Entry point
│   ├── runner.py                  # Orchestre core + adapters
│   ├── Dockerfile
│   └── requirements.txt
│
├── adapters/                      # I/O externes
│   ├── exchanges/                 # Binance WS + REST
│   ├── database/                  # SQLAlchemy + Alembic
│   ├── notifications/             # Telegram, Push, Email
│   └── cache/                     # Redis
│
├── api/                           # FastAPI backend
│   ├── main.py
│   ├── auth/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── middleware/
│   ├── Dockerfile
│   └── requirements.txt
│
├── ai_agent/                      # Agent IA
│   ├── agent.py
│   ├── tools.py
│   ├── providers.py
│   ├── telegram_handler.py
│   ├── backtester.py
│   ├── optimizer.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── notifier/                      # Service notifications
│   ├── main.py
│   ├── channels/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                      # React (WowDash)
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Overview.tsx
│   │   │   ├── Portfolio.tsx
│   │   │   ├── Trades.tsx
│   │   │   ├── StrategyBuilder.tsx
│   │   │   ├── Backtester.tsx
│   │   │   ├── AIAgent.tsx
│   │   │   ├── AIReports.tsx
│   │   │   ├── Alerts.tsx
│   │   │   ├── Logs.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/
│   │   ├── services/
│   │   ├── hooks/
│   │   └── types/
│   ├── Dockerfile
│   └── package.json
│
├── mobile/                        # React Native (Expo)
│   ├── app/
│   │   ├── (tabs)/
│   │   │   ├── overview.tsx
│   │   │   ├── portfolio.tsx
│   │   │   ├── strategies.tsx
│   │   │   ├── ai-agent.tsx
│   │   │   └── settings.tsx
│   │   └── trade/[id].tsx
│   ├── components/
│   ├── services/
│   └── package.json
│
├── tests/                         # Tests
│   ├── core/
│   ├── api/
│   ├── integration/
│   └── e2e/
│
├── scripts/                       # Utilitaires
│   ├── migrate_from_sniper.py     # Migration donnees
│   ├── seed_strategies.py         # Strategies par defaut
│   └── backup.sh                  # Backup DB
│
└── docs/                          # Documentation
    ├── API.md
    ├── INDICATORS.md
    └── DEPLOYMENT.md
```

---

## Annexe B : Estimation et Priorites

### Phase 1 : Foundation (2-3 semaines)

| Tache | Effort |
|-------|--------|
| Setup projet (repo, Docker, CI) | 1j |
| Core: models + indicators (25) | 4-5j |
| Core: evaluateur strategies | 2j |
| Core: risk management | 2j |
| Core: timeframe aggregator | 1j |
| Adapters: Binance WS + REST | 2j |
| Adapters: PostgreSQL | 1j |
| Engine: runner live | 2j |

### Phase 2 : API + Frontend (2-3 semaines)

| Tache | Effort |
|-------|--------|
| API: auth, trades, strategies | 3j |
| API: market, portfolio, alerts | 2j |
| API: WebSocket server | 1j |
| Frontend: Overview | 2j |
| Frontend: Trades | 1j |
| Frontend: Strategy Builder | 2j |
| Frontend: Backtester | 2j |
| Frontend: Settings | 1j |

### Phase 3 : Intelligence + Notifs (1-2 semaines)

| Tache | Effort |
|-------|--------|
| Notifier: Telegram | 1j |
| Notifier: Push (Firebase) | 1j |
| AI Agent: migration | 2j |
| AI Agent: chat web | 1j |
| AI Reports | 1j |
| Alertes systeme | 1j |

### Phase 4 : Mobile + Polish (2-3 semaines)

| Tache | Effort |
|-------|--------|
| Mobile: setup Expo | 1j |
| Mobile: 5 ecrans | 5j |
| Mobile: Push notifications | 1j |
| Mobile: WebSocket temps reel | 1j |
| Migration BTC Sniper Bot | 1j |
| Tests E2E | 2j |
| Documentation | 1j |
| Deploiement prod | 1j |

**Total estime : 8-11 semaines pour un produit complet.**

---

*Kairos Trading - Cahier des charges v1.0 - Fevrier 2026*
*"Saisir le moment opportun"*
