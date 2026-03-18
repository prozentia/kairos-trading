# Kairos Trading — Guide d'utilisation

## Sommaire

1. [Premiers pas](#1-premiers-pas)
2. [Dashboard](#2-dashboard)
3. [Controle du bot](#3-controle-du-bot)
4. [Strategies](#4-strategies)
5. [Trades et journal](#5-trades-et-journal)
6. [Portfolio](#6-portfolio)
7. [Performance](#7-performance)
8. [Alertes prix](#8-alertes-prix)
9. [Agent IA Telegram](#9-agent-ia-telegram)
10. [Notifications](#10-notifications)
11. [Reglages](#11-reglages)
12. [Backtests](#12-backtests)
13. [Gestion du risque](#13-gestion-du-risque)
14. [FAQ et depannage](#14-faq-et-depannage)

---

## 1. Premiers pas

### Acceder a Kairos

Ouvrez votre navigateur et rendez-vous sur :
- **Production** : `https://kairos.prozentia.com`
- **Dev** : `http://158.220.103.131:3002`

### Creer un compte

1. Cliquez sur **S'inscrire**
2. Renseignez :
   - **Nom d'utilisateur** (3 a 30 caracteres)
   - **Email**
   - **Mot de passe** (min. 8 caracteres, 1 majuscule, 1 chiffre)
3. Validez — vous etes automatiquement connecte

### Se connecter

1. Entrez votre email et mot de passe
2. Le token JWT est valide 15 minutes, renouvele automatiquement
3. Vous restez connecte 7 jours grace au refresh token

---

## 2. Dashboard

Le dashboard est la page d'accueil apres connexion. Il affiche en un coup d'oeil :

### Cartes metriques (haut de page)

| Metrique | Description |
|----------|-------------|
| **Valeur totale** | Balance + valeur des positions ouvertes (USDT) |
| **Balance disponible** | USDT disponible pour de nouveaux trades |
| **P&L du jour** | Profit ou perte depuis minuit (vert = positif, rouge = negatif) |
| **Exposition** | Pourcentage du capital investi dans des positions ouvertes |

### Graphique chandelier

- Graphique interactif en temps reel de la paire selectionnee
- Selecteur de paire en haut du graphique (BTC/USDT, ETH/USDT, etc.)
- Mise a jour automatique

### Positions actives

Tableau des positions ouvertes avec :
- Paire, direction (LONG/SHORT), prix d'entree, prix actuel
- Quantite, P&L en USDT et en %, stop-loss, strategie utilisee

### Trades recents

Les 8 derniers trades avec lien vers le detail.

### Controle du bot

Carte resumant l'etat du bot :
- **Statut** : En cours / Arrete
- **Mode** : LIVE (vert) ou DRY RUN (orange)
- **Strategie active**, uptime, nombre de positions
- **Niveau de confiance** : CRAWL (20) → WALK (52) → RUN (72) → SPRINT (90)
- Boutons **Demarrer / Arreter / Redemarrer**

> Les donnees se rafraichissent automatiquement toutes les 30 secondes.

---

## 3. Controle du bot

**Navigation** : Menu lateral → Bot

### Demarrer le trading

1. Assurez-vous que vos cles API Binance sont configurees (voir [Reglages](#11-reglages))
2. Configurez les parametres :

| Parametre | Description | Defaut |
|-----------|-------------|--------|
| **Dry Run** | Mode simulation (aucun ordre reel) | Active |
| **Paires** | Paires a surveiller (ex: BTCUSDT, ETHUSDT) | BTCUSDT |
| **Strategie** | Algorithme de trading a utiliser | msb_glissant |
| **Timeframe HA** | Timeframe d'analyse (tendance) | 1h |
| **Timeframe entree** | Timeframe pour les signaux d'entree | 5m |
| **Stop Loss (%)** | Perte max par trade | 2.0% |
| **Trailing activation (%)** | Seuil pour activer le trailing stop | 1.5% |
| **Trailing distance (%)** | Distance du trailing stop | 0.8% |
| **Capital par trade (USDT)** | Montant investi par position | 100 |
| **Balance complete** | Utiliser tout le solde disponible | Non |

3. Cliquez **Sauvegarder**
4. Cliquez **Demarrer**

### Mode Dry Run vs Live

| Mode | Comportement |
|------|-------------|
| **Dry Run** (orange) | Simule les trades sans passer d'ordres reels sur Binance. Parfait pour tester une strategie. |
| **Live** (vert) | Passe de vrais ordres sur Binance. Le capital est engage. |

> **Important** : Commencez toujours en Dry Run pour valider votre strategie avant de passer en Live.

### Consulter les logs

**Navigation** : Bot → Logs

- Logs en temps reel avec code couleur :
  - **Bleu** : DEBUG / INFO
  - **Orange** : WARNING
  - **Rouge** : ERROR
- Filtrage par niveau (All, Debug, Info, Warning, Error)
- Nombre de lignes : 50, 100, 200, 500
- Auto-refresh toutes les 3 secondes (desactivable)
- **Telecharger** les logs en fichier `.txt`

---

## 4. Strategies

**Navigation** : Menu lateral → Strategies

### Vue d'ensemble

La page affiche toutes vos strategies en grille avec :
- Nom et version
- Toggle actif/inactif
- Description
- Paires configurees
- Timeframe
- Nombre de conditions d'entree et de sortie
- Derniere modification

### Creer une strategie

1. Cliquez **Nouvelle strategie**
2. Remplissez les onglets :

#### Onglet General
- **Nom** (obligatoire)
- **Description**
- **Version** (ex: 1.0.0)
- **Timeframe** : 1m, 5m, 15m, 30m, 1h, 4h, 1d

#### Onglet Paires
- Tapez les paires separees par des virgules
- Ou cliquez sur les boutons rapides : BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, ADAUSDT, DOTUSDT, AVAXUSDT, LINKUSDT

#### Onglet Gestion du risque
- Stop Loss (%)
- Taille max de position (% du capital)
- Activation trailing stop (%)
- Distance trailing stop (%)

#### Onglet Conditions d'entree
Construisez vos conditions visuellement :
1. Choisissez un **indicateur** dans la liste (25+ disponibles)
2. Selectionnez un **operateur** : `<`, `>`, `=`, `cross_above`, `cross_below`
3. Definissez la **valeur** seuil
4. Combinez avec **ET / OU / NON**

Exemple : `RSI < 30 ET EMA(20) cross_above EMA(50)`

#### Onglet Conditions de sortie
Meme principe que les conditions d'entree.

#### Mode JSON
Pour les utilisateurs avances, basculez en mode JSON pour editer directement la definition de la strategie.

3. Cliquez **Valider** pour verifier la configuration
4. Cliquez **Creer**

### Indicateurs disponibles

| Categorie | Indicateurs |
|-----------|-------------|
| **Tendance** | EMA, SMA, MACD, Ichimoku, ADX, Parabolic SAR, Supertrend |
| **Momentum** | RSI, Stochastic, CCI, Williams %R, Momentum, ROC |
| **Volatilite** | Bollinger Bands, ATR, Keltner Channels, Donchian Channels |
| **Volume** | OBV, VWAP, Volume Profile |
| **Structure** | Market Structure Break (MSB), Order Blocks, Fair Value Gaps |
| **Autres** | Fibonacci, Heikin-Ashi |

### Actions sur une strategie

| Action | Description |
|--------|-------------|
| **Activer** | Le bot utilisera cette strategie pour le trading |
| **Desactiver** | La strategie reste sauvegardee mais non utilisee |
| **Dupliquer** | Cree une copie pour experimenter des variantes |
| **Modifier** | Ouvrir le builder pour editer |
| **Supprimer** | Suppression definitive |
| **Valider** | Verifier la coherence de la configuration |

---

## 5. Trades et journal

**Navigation** : Menu lateral → Trades

### Liste des trades

**Statistiques en haut de page** :
- Total trades, Win Rate (%), P&L total (USDT), Profit Factor

**Tableau** avec colonnes :
- Paire, Direction (LONG/SHORT), Prix d'entree, Prix de sortie
- Quantite, P&L (USDT), P&L (%), Duree, Strategie, Statut, Date

**Filtres** :
- Recherche par paire
- Statut : Tous, Ouvert, Ferme, Annule
- Strategie
- Bouton "Effacer les filtres"

**Export CSV** : Cliquez l'icone de telechargement pour exporter avec les filtres appliques.

### Detail d'un trade

Cliquez sur une ligne pour voir :
- Toutes les metriques du trade
- Raison d'entree et de sortie (si disponible)
- Frais payes

### Journal de trading

Sur la page detail d'un trade :
1. Ecrivez vos **notes** dans le champ texte (max 5000 caracteres)
2. Ajoutez des **tags** separes par des virgules (ex: `breakout, momentum, BTC`)
3. Cliquez **Ajouter**

Chaque entree de journal est horodatee et affichee chronologiquement.

> **Conseil** : Documentez systematiquement vos trades pour identifier les patterns gagnants et perdants.

---

## 6. Portfolio

**Navigation** : Menu lateral → Portfolio

### Vue d'ensemble

4 cartes metriques :
- **Valeur totale** du portefeuille
- **Balance disponible** en USDT
- **P&L du jour**
- **Exposition** (% du capital en positions)

### Courbe d'equite

Graphique sur 30 jours montrant l'evolution de votre P&L cumule.

### Allocation par actif

Graphique donut montrant la repartition de votre capital par paire (ex: 45% BTC, 30% ETH, 25% SOL).

### Positions ouvertes

Tableau detaille de chaque position :
- Paire, direction, prix d'entree, prix actuel
- Quantite, P&L courant, stop-loss, strategie

### Metriques de risque

| Metrique | Description |
|----------|-------------|
| **Drawdown** | Perte maximale depuis le plus haut |
| **Sharpe Ratio** | Rendement ajuste au risque (> 1 = bon) |
| **Sortino Ratio** | Comme Sharpe mais penalise uniquement les pertes |
| **Pertes consecutives** | Plus longue serie de trades perdants |

---

## 7. Performance

**Navigation** : Menu lateral → Performance

### KPI principaux

| KPI | Bon signe |
|-----|-----------|
| **Win Rate** | >= 50% (vert) |
| **R-Ratio moyen** | >= 1.5 (vert) |
| **P&L total** | Positif (vert) |
| **Max Drawdown** | < 15% (orange si depasse) |

### Statistiques journalieres

Tableau jour par jour avec :
- Nombre de trades
- Win Rate du jour
- P&L en USDT
- R-Ratio moyen
- Drawdown du jour

---

## 8. Alertes prix

### Creer une alerte

Via l'API ou l'agent Telegram :
- **Type** : prix au-dessus, prix en-dessous, croisement
- **Condition** : seuil de prix ou indicateur
- **Canaux** : Telegram, Push, Email

### Gerer les alertes

- Voir toutes les alertes actives
- Modifier ou supprimer une alerte
- Consulter l'historique des alertes declenchees

---

## 9. Agent IA Telegram

Kairos inclut un assistant IA conversationnel accessible via Telegram.

### Configuration

1. Renseignez `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID` dans les reglages
2. L'agent repond dans votre chat Telegram

### Commandes

| Commande | Description |
|----------|-------------|
| `/start` | Message de bienvenue |
| `/help` | Liste des commandes |
| `/status` | Etat du bot (running/stopped, mode, positions) |
| `/stats` | Statistiques des 7 derniers jours |
| `/portfolio` | Apercu du portefeuille |
| `/strategies` | Liste des strategies actives |
| `/alerts` | Alertes prix actives |
| `/risk` | Metriques de risque actuelles |
| `/clear` | Effacer l'historique de conversation |

### Conversations naturelles

L'agent comprend le langage naturel. Exemples :

- *"Quel est mon P&L cette semaine ?"*
- *"Analyse technique de BTC sur le 4h"*
- *"Lance un backtest de la strategie MSB sur les 30 derniers jours"*
- *"Cree une alerte si ETH depasse 4000$"*
- *"Quel est mon drawdown actuel ?"*
- *"Montre-moi les 5 derniers trades"*
- *"Desactive la strategie Momentum"*

### Outils disponibles

L'agent dispose de 10+ outils qu'il utilise automatiquement :

| Outil | Ce qu'il fait |
|-------|---------------|
| `get_bot_status` | Statut, uptime, mode, positions ouvertes |
| `get_trade_history` | Historique avec filtres (paire, periode, statut) |
| `get_trade_stats` | Win rate, P&L, Sharpe, Sortino, profit factor |
| `get_portfolio` | Balance, exposition, positions detaillees |
| `get_market_analysis` | Analyse technique multi-timeframe avec indicateurs |
| `list_strategies` | Toutes les strategies et leur statut |
| `get_strategy_detail` | Configuration complete d'une strategie |
| `run_backtest` | Lancer un test historique sur une strategie |
| `get_alerts` | Alertes actives et historique |
| `create_alert` | Creer une nouvelle alerte prix |
| `get_risk_metrics` | Drawdown, exposition, serie de pertes |

**Modele IA** : Claude Sonnet 4 via OpenRouter (configurable).

---

## 10. Notifications

Kairos envoie des notifications en temps reel sur plusieurs canaux.

### Canaux disponibles

| Canal | Usage |
|-------|-------|
| **Telegram** | Alertes trades, statut bot, rapports |
| **Push mobile** | Notifications Firebase (app mobile) |
| **Email** | Rapports journaliers, alertes critiques |
| **In-app** | Notifications dans le dashboard (WebSocket) |

### Evenements notifies

| Evenement | Contenu |
|-----------|---------|
| **Trade ouvert** | Paire, prix d'entree, strategie, taille |
| **Trade ferme** | P&L en USDT et %, duree, raison de sortie |
| **Stop-loss touche** | Paire, perte, prix de sortie |
| **Bot demarre/arrete** | Statut, mode, paires actives |
| **Erreur critique** | Message d'erreur, circuit breaker |
| **Rapport journalier** | Resume envoye a 9h00 |
| **Rapport IA** | Analyse generee disponible |

### Configurer les notifications

**Navigation** : Reglages → Notifications

Activez/desactivez individuellement :
- Trade ouvert
- Trade ferme
- Changements statut bot
- Rapport journalier
- Alertes erreur

---

## 11. Reglages

**Navigation** : Menu lateral → Reglages

### Onglet Cles API

#### Binance
- **API Key** et **API Secret**
- Utilisez les cles du **testnet** pour les tests
- En production, activez uniquement **Spot Trading** et **Read** — jamais les retraits

#### Telegram
- **Bot Token** : obtenez-le via @BotFather sur Telegram
- **Chat ID** : votre identifiant de chat Telegram

### Onglet Notifications

Toggles pour chaque type de notification (voir section precedente).

### Onglet Apparence

Choisissez votre theme :
- **Clair** (icone soleil)
- **Sombre** (icone lune) — recommande pour le trading
- **Systeme** — suit les preferences de votre OS

### Profil

**Navigation** : Reglages → Profil

- Modifier votre nom d'utilisateur et email
- Changer votre mot de passe
- Voir la date de creation du compte

---

## 12. Backtests

### Lancer un backtest

1. Allez sur le detail d'une strategie
2. Cliquez **Backtest**
3. Configurez :
   - **Paire** a tester
   - **Date de debut** et **date de fin**
4. Lancez — le backtest s'execute en arriere-plan

### Consulter les resultats

- P&L total simule
- Nombre de trades
- Win rate
- Drawdown maximum
- Courbe d'equite simulee

### Comparer des backtests

Selectionnez plusieurs backtests pour les comparer cote a cote :
- Performances relatives
- Metriques de risque
- Courbes d'equite superposees

> **Conseil** : Testez votre strategie sur au moins 30 jours avant de passer en Live.

---

## 13. Gestion du risque

Kairos integre plusieurs mecanismes de protection automatiques.

### Niveaux de protection

| Mecanisme | Description | Configuration |
|-----------|-------------|---------------|
| **Stop-Loss** | Limite la perte par trade | % configurable par strategie |
| **Trailing Stop** | Suit le prix a la hausse, protege les gains | Activation + distance en % |
| **Stop-Loss serveur** | Double protection : ordre stop sur Binance en plus du local | Automatique |
| **Perte journaliere max** | Arrete le bot si la perte du jour depasse le seuil | `KAIROS_MAX_DAILY_LOSS_PCT` (defaut: 5%) |
| **Drawdown max** | Arrete le bot si le drawdown total depasse le seuil | `KAIROS_MAX_DRAWDOWN_PCT` (defaut: 15%) |
| **Max positions** | Limite le nombre de positions simultanees | `KAIROS_MAX_POSITIONS` (defaut: 3) |
| **Position sizing** | Calcul Kelly criterion + niveau de confiance | Automatique |

### Niveaux de confiance (Trust Level)

Le bot ajuste automatiquement la taille des positions selon sa confiance :

| Niveau | Score | Comportement |
|--------|-------|-------------|
| **CRAWL** | 20 | Positions minimales, mode prudent |
| **WALK** | 52 | Taille moderee |
| **RUN** | 72 | Taille normale |
| **SPRINT** | 90 | Taille maximale, haute confiance |

Le score augmente avec les trades gagnants consecutifs et diminue avec les pertes.

### Risk Gate (validation pre-trade)

Avant chaque trade, le systeme verifie :
- Le spread est-il acceptable ?
- Le slippage estime est-il dans les limites ?
- Le score de confiance est-il suffisant ?
- L'exposition totale reste-t-elle sous le seuil ?
- La perte journaliere n'est-elle pas deja atteinte ?

Si un critere echoue, le trade est refuse.

---

## 14. FAQ et depannage

### Le bot ne demarre pas

1. Verifiez que les cles API Binance sont valides (Reglages → Cles API)
2. Consultez les logs (Bot → Logs) pour identifier l'erreur
3. Assurez-vous qu'au moins une paire est configuree
4. Verifiez la connexion aux services : `docker compose ps`

### Mes trades ne s'executent pas

1. Verifiez que le mode **Dry Run** est desactive pour le trading reel
2. Verifiez que votre strategie est **activee**
3. Consultez les logs pour les signaux generes
4. Verifiez votre balance sur Binance

### Le P&L affiche est different de Binance

- Kairos calcule le P&L avec les frais inclus
- Les prix peuvent differer legerement selon le moment de la lecture
- En Dry Run, les prix sont simules et peuvent diverger

### L'agent Telegram ne repond pas

1. Verifiez `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID` dans les reglages
2. Verifiez que le container `kairos-ai-agent` est actif : `docker logs kairos-ai-agent --tail=20`
3. Verifiez que `OPENROUTER_API_KEY` est configure

### Comment reinitialiser mon mot de passe ?

Utilisez la page "Mot de passe oublie" sur l'ecran de connexion, ou changez-le via Reglages → Profil.

### Comment sauvegarder ma configuration ?

**Navigation** : Reglages → Backup

- **Exporter** : Telecharge un fichier JSON avec toute votre configuration
- **Importer** : Restaurer a partir d'un fichier exporte

### Commandes Docker utiles

```bash
# Statut des services
docker compose ps

# Logs du moteur de trading
docker logs kairos-engine --tail=50 -f

# Logs de l'API
docker logs kairos-api --tail=50 -f

# Redemarrer un service
docker compose restart engine

# Backup de la base de donnees
docker exec kairos-db pg_dump -U kairos kairos > backup-$(date +%Y%m%d).sql

# Restaurer un backup
cat backup.sql | docker exec -i kairos-db psql -U kairos kairos
```

---

## Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl+K` | Recherche rapide |
| `D` | Aller au Dashboard |
| `T` | Aller aux Trades |
| `S` | Aller aux Strategies |
| `B` | Aller au Bot |

---

## Securite

- **Ne partagez jamais** vos cles API Binance
- Activez uniquement les permissions **Spot Trading** et **Read** sur Binance
- **Desactivez les retraits** dans les permissions de la cle API
- Utilisez un **mot de passe fort** (8+ caracteres, majuscule, chiffre)
- En production, Kairos est accessible uniquement via **HTTPS** (Let's Encrypt)
- Les tokens JWT expirent apres 15 minutes
- Les mots de passe sont haches avec **bcrypt**

---

*Kairos Trading — Bot de trading automatise multi-paires*
*Documentation generee le 18/03/2026*
