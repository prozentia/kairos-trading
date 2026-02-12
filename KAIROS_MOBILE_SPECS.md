# KAIROS TRADING - App Mobile - Cahier des Charges

> Specification complete pour l'application mobile iOS + Android.
> A realiser APRES le bot et le dashboard web.
> L'API Kairos doit etre deployee et fonctionnelle avant de commencer le mobile.

---

## Table des Matieres

1. [Vision et Objectifs](#1-vision-et-objectifs)
2. [Specifications Fonctionnelles](#2-specifications-fonctionnelles)
3. [Wireframes / UX-UI](#3-wireframes--ux-ui)
4. [Architecture Technique](#4-architecture-technique)
5. [Navigation et Ecrans](#5-navigation-et-ecrans)
6. [Notifications Push](#6-notifications-push)
7. [Mode Offline](#7-mode-offline)
8. [Securite](#8-securite)
9. [Performance](#9-performance)
10. [Publication Stores](#10-publication-stores)
11. [Testing](#11-testing)
12. [Estimation](#12-estimation)

---

## 1. Vision et Objectifs

### 1.1 Vision

L'app mobile Kairos est le **compagnon de poche** du trader. Elle offre un controle complet du bot de trading depuis n'importe ou : monitoring temps reel, gestion des positions, activation de strategies, chat IA et alertes push instantanees.

### 1.2 Objectifs

| Objectif | Metrique |
|----------|----------|
| Temps de chargement | < 2 secondes (cold start) |
| Mise a jour prix | Temps reel via WebSocket |
| Notification push | < 3 secondes apres l'evenement |
| Disponibilite offline | Donnees cachees consultables |
| Stores | App Store + Play Store |
| Note cible | 4.5+ etoiles |

### 1.3 Utilisateurs Cibles

| Persona | Usage |
|---------|-------|
| **Trader actif** | Monitoring continu, reactivite aux alertes, ajustement des strategies en mobilite |
| **Investisseur** | Consultation quotidienne du P&L, rapports hebdomadaires |
| **Futur SaaS** | Utilisateurs copy-trading, abonnement premium |

### 1.4 Dependances

L'app mobile depend de :
- **Kairos API** (FastAPI) : tous les endpoints REST + WebSocket
- **Firebase Cloud Messaging** : notifications push
- **Apple Push Notification Service** : notifications iOS
- **Kairos WebSocket** : prix temps reel, positions, signaux

L'app ne communique **jamais** directement avec Binance. Tout passe par l'API Kairos.

---

## 2. Specifications Fonctionnelles

### 2.1 Authentification

| Feature | Description |
|---------|-------------|
| Login email/password | Ecran de connexion classique |
| Biometrie | Face ID / Touch ID / Empreinte Android |
| Remember me | Token stocke dans Secure Storage |
| Auto-lock | Verrouillage apres 5 min d'inactivite (configurable) |
| Refresh token | Renouvellement automatique, transparent |
| Logout | Invalidation du token + suppression du cache |
| 2FA (TOTP) | Google Authenticator / Authy |
| Session management | Voir les sessions actives, revoquer a distance |

### 2.2 Dashboard (Overview)

| Feature | Description | Source |
|---------|-------------|--------|
| Prix actuel | BTC/USDT (ou paire principale) avec sparkline 24h | WebSocket |
| Variation 24h | Pourcentage + valeur absolue, couleur vert/rouge | WebSocket |
| Statut bot | Running/Stopped, uptime, mode DRY-RUN/LIVE | Poll 10s |
| Strategie active | Nom de la strategie en cours | Poll 30s |
| Position ouverte | Entry, qty, P&L non-realise, SL, duree | WebSocket |
| Solde compte | USDT + BTC + valeur totale en USD | WebSocket |
| KPIs du jour | Trades, win rate, P&L | Poll 30s |
| Mini equity curve | Sparkline du P&L sur 7 jours | Poll 5min |
| Trades recents | 5 derniers trades avec P&L | Poll 30s |
| Multi-paires | Liste des paires actives avec prix et signal | WebSocket |
| Pull-to-refresh | Rafraichir toutes les donnees | Manuel |

### 2.3 Portfolio

| Feature | Description |
|---------|-------------|
| Positions ouvertes | Liste avec P&L temps reel par position |
| Detail position | Entry, SL, TP, trailing, duree, strategie |
| Fermer position | Bouton "Vendre maintenant" avec confirmation |
| Allocation | Graphique donut par paire |
| Exposure | % du capital engage |
| Equity curve | Graphique interactif (pinch-to-zoom, pan) |
| Performance par paire | P&L par paire sur la periode selectionnee |
| Drawdown | Drawdown actuel + max historique |

### 2.4 Historique des Trades

| Feature | Description |
|---------|-------------|
| Liste scrollable | Infinite scroll, charge 20 trades a la fois |
| Filtres | Par paire, par strategie, par resultat (gain/perte), par date |
| Recherche | Texte libre dans notes et raisons |
| Detail trade | Ecran complet avec toutes les infos + mini graphique |
| Journal | Ajouter des notes, tags a un trade |
| Statistiques | KPIs en haut de la liste (win rate, P&L moyen, etc.) |
| Tri | Par date, P&L, duree |
| Swipe actions | Swipe gauche = ajouter note, swipe droit = partager |

### 2.5 Strategies

| Feature | Description |
|---------|-------------|
| Liste des strategies | Nom, statut (active/inactive/validee), derniere perf |
| Detail strategie | Conditions d'entree/sortie en lecture, risk management, filtres |
| Activer/Desactiver | Toggle avec confirmation |
| Statistiques | Win rate, P&L, nombre de trades par strategie |
| **Pas de creation/edition** | Trop complexe pour mobile. Redirection vers le web. |
| Comparer | Selectionner 2 strategies et voir les metriques cote a cote |

> **Note** : La creation et l'edition de strategies se font sur le web (Strategy Builder). L'app mobile permet de les consulter et les activer/desactiver.

### 2.6 Backtester

| Feature | Description |
|---------|-------------|
| Lancer un backtest | Choix strategie + paire + periode + capital |
| Progression | Barre de progression en temps reel |
| Resultats | KPI cards + equity curve + liste trades |
| Historique | Liste des backtests passes |
| Comparer | Selectionner 2 backtests |

### 2.7 Agent IA (Chat)

| Feature | Description |
|---------|-------------|
| Chat conversationnel | Interface type messagerie (bulles) |
| Commandes rapides | Boutons `/status`, `/stats`, `/portfolio`, `/risk` |
| Reponses riches | Tableaux, graphiques inline, metriques |
| Historique | Conversations passees |
| Contexte | L'agent connait l'etat du bot et du portfolio |
| Input vocal | Speech-to-text pour dicter les questions (optionnel phase 2) |

### 2.8 Alertes

| Feature | Description |
|---------|-------------|
| Liste des alertes | Actives et declenchees |
| Creer une alerte | Prix atteint X, RSI > Y, drawdown > Z |
| Templates | Alertes pre-configurees (SL touche, nouveau trade, etc.) |
| Toggle on/off | Activer/desactiver sans supprimer |
| Historique | Alertes declenchees avec timestamp |
| Supprimer | Swipe pour supprimer |

### 2.9 Controle du Bot

| Feature | Description |
|---------|-------------|
| Start/Stop | Boutons avec confirmation (surtout pour LIVE) |
| Restart | Redemarrage avec confirmation |
| Mode toggle | DRY-RUN ↔ LIVE avec double confirmation + biometrie |
| Logs temps reel | Stream des derniers logs (scrollable) |
| Health | Indicateur de sante (uptime, derniere activite, erreurs) |

### 2.10 Parametres

| Feature | Description |
|---------|-------------|
| Profil | Nom, email, timezone, langue |
| Notifications | Toggle par type (trades, alertes, erreurs, rapports) |
| Apparence | Theme (auto/sombre/clair), taille texte |
| Securite | Biometrie on/off, auto-lock delai, 2FA, sessions |
| Trading | Paires actives, capital, risk limits (lecture seule si LIVE) |
| Cache | Voir taille du cache, vider |
| A propos | Version, changelog, support |
| Danger zone | Deconnexion, supprimer compte |

---

## 3. Wireframes / UX-UI

### 3.1 Design System

#### Palette de Couleurs (Theme Sombre Trading)

```
COULEURS PRINCIPALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Background principal     #0B0E11    (quasi-noir, style Binance)
Background carte         #1E2329    (gris tres fonce)
Background sureleve      #2B3139    (gris fonce)
Surface active           #363C45    (gris moyen)

Texte principal          #EAECEF    (blanc casse)
Texte secondaire         #848E9C    (gris clair)
Texte desactive          #5E6673    (gris)

Accent positif (gain)    #0ECB81    (vert Binance)
Accent negatif (perte)   #F6465D    (rouge Binance)
Accent primaire          #F0B90B    (jaune/or Kairos)
Accent info              #1E90FF    (bleu)
Accent warning           #FFA500    (orange)

Bordures                 #2B3139    (subtile)
Separateurs              #1E2329
```

#### Typographie

```
Font principale   : Inter (Google Fonts, gratuit)
Font monospace    : JetBrains Mono (pour les prix et chiffres)

Tailles :
  H1 (titre ecran)   : 24px, Bold
  H2 (section)        : 20px, SemiBold
  H3 (sous-titre)     : 16px, SemiBold
  Body                : 14px, Regular
  Caption             : 12px, Regular
  Prix large          : 32px, Bold, JetBrains Mono
  Prix inline         : 16px, Medium, JetBrains Mono
  Badge               : 11px, SemiBold, uppercase
```

#### Composants de Base

```
CARTE (Card)
┌─────────────────────────┐
│  bg: #1E2329            │
│  border-radius: 16px    │
│  padding: 16px          │
│  shadow: none           │
│  border: 1px #2B3139    │
└─────────────────────────┘

BOUTON PRIMAIRE
┌─────────────────────────┐
│  bg: #F0B90B            │
│  text: #0B0E11 (noir)   │
│  border-radius: 12px    │
│  height: 48px           │
│  font: 16px SemiBold    │
└─────────────────────────┘

BOUTON DANGER
┌─────────────────────────┐
│  bg: #F6465D            │
│  text: #FFFFFF           │
│  border-radius: 12px    │
└─────────────────────────┘

BADGE POSITIF          BADGE NEGATIF
┌──────────┐           ┌──────────┐
│ +0.45%   │           │ -0.32%   │
│ bg:#0ECB81/15        │ bg:#F6465D/15
│ txt:#0ECB81│          │ txt:#F6465D│
└──────────┘           └──────────┘

INPUT
┌─────────────────────────┐
│  bg: #2B3139            │
│  border: 1px #363C45    │
│  border-radius: 12px    │
│  text: #EAECEF          │
│  placeholder: #5E6673   │
│  height: 48px           │
└─────────────────────────┘
```

### 3.2 Ecran : Splash / Loading

```
┌─────────────────────────┐
│                         │
│                         │
│                         │
│                         │
│         ◆               │
│       KAIROS             │
│      TRADING             │
│                         │
│      ● ● ○ (loading)   │
│                         │
│                         │
│                         │
│                         │
│   bg: #0B0E11           │
│   logo: #F0B90B (or)    │
└─────────────────────────┘
```

### 3.3 Ecran : Login

```
┌─────────────────────────┐
│                         │
│         ◆               │
│       KAIROS             │
│                         │
│  ┌───────────────────┐  │
│  │ ✉ Email           │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │ 🔒 Mot de passe   │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │   SE CONNECTER    │  │  ← Bouton primaire (or)
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │  🔐 Face ID       │  │  ← Si deja connecte
│  └───────────────────┘  │
│                         │
│  Mot de passe oublie ?  │  ← Lien
│                         │
└─────────────────────────┘
```

### 3.4 Ecran : Overview (Tab 1 - Home)

```
┌─────────────────────────┐
│ KAIROS           🔔3  ⚙ │  ← Header fixe
├─────────────────────────┤
│                         │
│  BTC / USDT             │
│  $67,234.50             │  ← 32px, Bold, JetBrains Mono
│  +$1,523.40 (+2.32%)   │  ← Vert #0ECB81
│  ▁▃▅▇▆▅▇█▇▅▃▅▇         │  ← Sparkline 24h
│                         │
│ ┌─────────┐┌──────────┐ │
│ │ ● Bot   ││ 💼 Solde │ │
│ │ Actif   ││ 270 USDT │ │
│ │ 14h23m  ││ 0.002BTC │ │
│ │ Scalp.  ││ $270 tot │ │
│ └─────────┘└──────────┘ │
│                         │
│ POSITION OUVERTE        │
│ ┌───────────────────────┐│
│ │ BTC/USDT  LONG       ││
│ │                      ││
│ │ Entry   $67,100      ││
│ │ Actuel  $67,234      ││
│ │ P&L     +$0.30  ● +0.20% ││  ← Badge vert
│ │                      ││
│ │ SL ████░░░░░░ $66,225││  ← Barre visuelle
│ │ TP ██████████ Trailing││
│ │                      ││
│ │ ⏱ 2h 15min           ││
│ │                      ││
│ │ [  Vendre Maintenant ]││  ← Bouton danger (rouge)
│ └───────────────────────┘│
│                         │
│ AUJOURD'HUI             │
│ ┌──────┐┌──────┐┌──────┐│
│ │Trade ││ Win  ││ P&L  ││
│ │  3   ││ 67%  ││+$1.85││
│ └──────┘└──────┘└──────┘│
│                         │
│ TRADES RECENTS          │
│ ┌───────────────────────┐│
│ │ #47 BUY  BTC  +0.45% ● ││
│ │ 10:23     Scalping    ││
│ ├───────────────────────┤│
│ │ #46 SELL BTC  -0.32% ○ ││
│ │ 09:15     Stop-Loss   ││
│ ├───────────────────────┤│
│ │ #45 SELL BTC  +1.23% ● ││
│ │ 08:02     Trailing    ││
│ └───────────────────────┘│
│                         │
├─────────────────────────┤
│ 📊    💼    🎯   🤖   ⚙│  ← Tab bar
│ Home  Port  Strat  AI  Set│
└─────────────────────────┘
```

### 3.5 Ecran : Portfolio (Tab 2)

```
┌─────────────────────────┐
│ ← Portfolio             │
├─────────────────────────┤
│                         │
│ CAPITAL TOTAL           │
│ $270.50                 │  ← Grand, bold
│ +$12.45 (+4.8%)         │  ← Depuis le debut
│                         │
│ ┌───────────────────────┐│
│ │  EQUITY CURVE         ││
│ │                       ││
│ │   ╱──╲    ╱──────    ││
│ │  ╱    ╲╱╱─           ││
│ │ ╱                     ││
│ │                       ││
│ │ [7j] [30j] [90j] [All]││
│ └───────────────────────┘│
│                         │
│ ┌──────┐┌──────┐┌──────┐│
│ │Posit.││Expos.││Drawdn││
│ │ 2/5  ││ 67%  ││-2.1% ││
│ └──────┘└──────┘└──────┘│
│                         │
│ POSITIONS OUVERTES      │
│ ┌───────────────────────┐│
│ │ BTC/USDT         LONG ││
│ │ $67,100 → $67,234    ││
│ │ ┃████████░░┃  +0.20% ││  ← Barre P&L visuelle
│ │ 0.001 BTC   SL:$66.2k││
│ ├───────────────────────┤│
│ │ SOL/USDT         LONG ││
│ │ $123.40 → $124.50    ││
│ │ ┃██████████████┃+0.89%││
│ │ 0.8 SOL    SL:$121.5 ││
│ └───────────────────────┘│
│                         │
│ ALLOCATION              │
│ ┌───────────────────────┐│
│ │    ┌────┐             ││
│ │   ┌┤USDT├┐ 33%       ││
│ │  ┌┤│    │├┐           ││
│ │  │BTC   SOL│          ││
│ │  │ 40%  27%│          ││
│ └───────────────────────┘│
│                         │
│ PERFORMANCE PAR PAIRE   │
│ ┌───────────────────────┐│
│ │ BTC   23 trades +$8.2 ││
│ │ SOL   12 trades +$4.3 ││
│ └───────────────────────┘│
│                         │
├─────────────────────────┤
│ 📊    💼    🎯   🤖   ⚙│
└─────────────────────────┘
```

### 3.6 Ecran : Detail d'un Trade

```
┌─────────────────────────┐
│ ← Trade #47             │
├─────────────────────────┤
│                         │
│  BTC / USDT             │
│  ┌───────────────────┐  │
│  │ ● PROFIT          │  │  ← Badge vert
│  │ +$0.40 (+0.60%)   │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │  Mini-graphique   │  │
│  │  bougies avec     │  │
│  │  🔼 entry marker  │  │
│  │  🔽 exit marker   │  │
│  └───────────────────┘  │
│                         │
│  DETAILS                │
│  ─────────────────────  │
│  Entree     $67,100.00  │
│  Sortie     $67,500.00  │
│  Quantite   0.00148 BTC │
│  Frais      $0.04       │
│  P&L Net    +$0.36      │
│                         │
│  TIMING                 │
│  ─────────────────────  │
│  Ouverture  10:23:45    │
│  Fermeture  10:48:12    │
│  Duree      24 min 27s  │
│                         │
│  STRATEGIE              │
│  ─────────────────────  │
│  Nom       Scalping Hard│
│  Raison    RSI bounce + │
│            MACD cross    │
│  Sortie    Trailing Stop│
│                         │
│  JOURNAL                │
│  ─────────────────────  │
│  Tags: [scalp] [btc]   │
│                         │
│  Notes:                 │
│  (aucune note)          │
│  [+ Ajouter une note]   │
│                         │
└─────────────────────────┘
```

### 3.7 Ecran : Strategies (Tab 3)

```
┌─────────────────────────┐
│ ← Strategies            │
├─────────────────────────┤
│                         │
│ [Voir sur le web ↗]     │  ← Pour creer/editer
│                         │
│ STRATEGIE ACTIVE        │
│ ┌───────────────────────┐│
│ │ ★ Scalping Hard  ●ON  ││
│ │                       ││
│ │ 23 trades │ 65% win   ││
│ │ P&L: +$12.45          ││
│ │                       ││
│ │ Entree: RSI<30 AND    ││
│ │   MACD hist+ AND HA ↑ ││
│ │ Sortie: RSI>75 OR HA↓ ││
│ │                       ││
│ │ SL: 1.5% │ Trail: 0.6%││
│ │                       ││
│ │ [Desactiver]          ││
│ └───────────────────────┘│
│                         │
│ AUTRES STRATEGIES       │
│ ┌───────────────────────┐│
│ │ ○ RSI Bounce    ✅Val ││
│ │   12 trades │ 58% win ││
│ │   [Activer]           ││
│ ├───────────────────────┤│
│ │ ○ MSB Glissant  ✅Val ││
│ │   8 trades │ 63% win  ││
│ │   [Activer]           ││
│ ├───────────────────────┤│
│ │ ○ MACD Momentum ❌    ││
│ │   Non validee         ││
│ │   [Valider d'abord]   ││
│ └───────────────────────┘│
│                         │
│ COMPARER                │
│ ┌───────────────────────┐│
│ │ Selectionner 2 strat. ││
│ │ pour comparer les     ││
│ │ performances.         ││
│ │                       ││
│ │ [Comparer]            ││
│ └───────────────────────┘│
│                         │
├─────────────────────────┤
│ 📊    💼    🎯   🤖   ⚙│
└─────────────────────────┘
```

### 3.8 Ecran : Agent IA (Tab 4)

```
┌─────────────────────────┐
│ ← Agent IA     [Rapport]│
├─────────────────────────┤
│                         │
│  ┌───────────────────┐  │
│  │ 🤖 Bonjour ! Je   │  │  ← Bulle agent (bg #1E2329)
│  │ suis Kairos. Posez │  │
│  │ moi vos questions. │  │
│  └───────────────────┘  │
│                         │
│      ┌───────────────┐  │
│      │ Quel est le   │  │  ← Bulle user (bg #F0B90B/20)
│      │ statut ?       │  │
│      └───────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │ 🤖 Voici l'etat : │  │
│  │                   │  │
│  │ ● Bot actif 14h   │  │
│  │ ● BTC LONG +0.2%  │  │
│  │ ● Solde: 136 USDT │  │
│  │ ● 3 trades auj.   │  │
│  │   (2W / 1L)       │  │
│  └───────────────────┘  │
│                         │
│      ┌───────────────┐  │
│      │ Compare les   │  │
│      │ strategies    │  │
│      └───────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │ 🤖 Comparaison :  │  │
│  │ ┌─────┬────┬────┐ │  │
│  │ │Strat│Win%│P&L │ │  │
│  │ │Scalp│63% │+$12│ │  │
│  │ │RSI  │58% │+$8 │ │  │
│  │ │MSB  │67% │+$15│ │  │
│  │ └─────┴────┴────┘ │  │
│  │                   │  │
│  │ MSB Glissant a la │  │
│  │ meilleure perf.   │  │
│  └───────────────────┘  │
│                         │
│ RACCOURCIS              │
│ ┌─────┐┌─────┐┌──────┐ │
│ │/stat││/port││/risk │ │  ← Boutons horizontaux scrollables
│ └─────┘└─────┘└──────┘ │
│ ┌─────┐┌─────┐┌──────┐ │
│ │/sug ││/comp││/back │ │
│ └─────┘└─────┘└──────┘ │
│                         │
│ ┌───────────────────┬──┐│
│ │ Message...        │➤ ││  ← Input + send
│ └───────────────────┴──┘│
│                         │
├─────────────────────────┤
│ 📊    💼    🎯   🤖   ⚙│
└─────────────────────────┘
```

### 3.9 Ecran : Alertes

```
┌─────────────────────────┐
│ ← Alertes         [+ ⊕]│
├─────────────────────────┤
│                         │
│ ALERTES ACTIVES    (3)  │
│ ┌───────────────────────┐│
│ │ 🔔 BTC > $68,000     ││
│ │ Push + Telegram  [ON] ││
│ ├───────────────────────┤│
│ │ 🔔 RSI(14) < 25      ││
│ │ Push only       [ON]  ││
│ ├───────────────────────┤│
│ │ 🔔 Drawdown > 5%     ││
│ │ Push + Telegram  [ON] ││
│ └───────────────────────┘│
│                         │
│ DECLENCHEES RECEMMENT   │
│ ┌───────────────────────┐│
│ │ ✅ BTC < $66,000     ││
│ │ 09:15 UTC - il y a 2h││
│ ├───────────────────────┤│
│ │ ✅ Stop-Loss #46     ││
│ │ 09:15 UTC - il y a 2h││
│ └───────────────────────┘│
│                         │
├─────────────────────────┤
│ 📊    💼    🎯   🤖   ⚙│
└─────────────────────────┘
```

### 3.10 Ecran : Creer une Alerte

```
┌─────────────────────────┐
│ ← Nouvelle Alerte       │
├─────────────────────────┤
│                         │
│ TYPE                    │
│ ┌───────────────────┐   │
│ │ [Prix ●] [Indic.] │   │
│ │ [P&L   ] [System] │   │
│ └───────────────────┘   │
│                         │
│ CONDITION               │
│ Paire: [BTC/USDT ▼]    │
│ Quand le prix           │
│ [depasse ▼] [$68,000 ]  │
│                         │
│ CANAUX                  │
│ [✅] Push notification  │
│ [✅] Telegram           │
│ [  ] Email              │
│                         │
│ NOM (optionnel)         │
│ [BTC breakout $68k    ] │
│                         │
│ ┌───────────────────┐   │
│ │   CREER L'ALERTE  │   │  ← Bouton primaire
│ └───────────────────┘   │
│                         │
└─────────────────────────┘
```

### 3.11 Ecran : Controle du Bot

```
┌─────────────────────────┐
│ ← Controle Bot          │
├─────────────────────────┤
│                         │
│         ┌───┐           │
│         │ ● │           │  ← Grand indicateur vert/rouge
│         └───┘           │
│      BOT ACTIF          │
│    depuis 14h 23min     │
│                         │
│ Mode: ⚡ LIVE           │  ← Badge jaune/or
│ Strategie: Scalping Hard│
│ Paires: BTC, SOL        │
│                         │
│ ┌──────────┐┌──────────┐│
│ │ ⏸ PAUSE  ││ 🔄 RESTART│  ← Boutons d'action
│ └──────────┘└──────────┘│
│                         │
│ ┌───────────────────────┐│
│ │ 🔴 ARRETER LE BOT    ││  ← Bouton danger
│ └───────────────────────┘│
│                         │
│ ── MODE DE TRADING ──   │
│ ┌───────────────────────┐│
│ │ DRY-RUN    ○  ●  LIVE││  ← Toggle avec confirmation
│ └───────────────────────┘│
│ ⚠ Changer le mode       │
│ necessite une double    │
│ confirmation + biometrie│
│                         │
│ ── SANTE ──             │
│ ┌───────────────────────┐│
│ │ API Binance    ● OK   ││
│ │ WebSocket      ● OK   ││
│ │ Base de donnees● OK   ││
│ │ Derniere activite     ││
│ │   il y a 3 secondes   ││
│ │ Erreurs (24h): 0      ││
│ └───────────────────────┘│
│                         │
│ ── LOGS RECENTS ──      │
│ ┌───────────────────────┐│
│ │ 11:52 [INFO] ANALYSE  ││
│ │  Prix: $67,234 HA:VERT││
│ │ 11:52 [INFO] EMA_50   ││
│ │  calculated            ││
│ │ 11:51 [INFO] ANALYSE  ││
│ │  Signal: NO_SIGNAL     ││
│ │ ...                    ││
│ └───────────────────────┘│
│                         │
└─────────────────────────┘
```

### 3.12 Ecran : Settings (Tab 5)

```
┌─────────────────────────┐
│ ← Parametres            │
├─────────────────────────┤
│                         │
│ PROFIL                  │
│ ┌───────────────────────┐│
│ │ 👤 Jalal              ││
│ │ jalal@prozentia.com   ││
│ │ Timezone: UTC+1       ││
│ │ Langue: Francais      ││
│ │                  [>]  ││
│ └───────────────────────┘│
│                         │
│ NOTIFICATIONS           │
│ ┌───────────────────────┐│
│ │ Trades BUY/SELL  [ON] ││
│ │ Stop-Loss        [ON] ││
│ │ Alertes          [ON] ││
│ │ Rapports IA      [OFF]││
│ │ Erreurs bot      [ON] ││
│ │ Son              [ON] ││
│ │ Vibration        [ON] ││
│ └───────────────────────┘│
│                         │
│ APPARENCE               │
│ ┌───────────────────────┐│
│ │ Theme    [● Auto]     ││
│ │          [  Sombre]   ││
│ │          [  Clair]    ││
│ └───────────────────────┘│
│                         │
│ SECURITE                │
│ ┌───────────────────────┐│
│ │ Biometrie        [ON] ││
│ │ Auto-lock     [5 min] ││
│ │ 2FA          [Active] ││
│ │ Sessions actives  [>] ││
│ └───────────────────────┘│
│                         │
│ BOT & TRADING           │
│ ┌───────────────────────┐│
│ │ Controle du bot   [>] ││
│ │ Risk limits       [>] ││
│ │ Paires actives    [>] ││
│ └───────────────────────┘│
│                         │
│ DONNEES                 │
│ ┌───────────────────────┐│
│ │ Cache: 12.3 MB        ││
│ │ [Vider le cache]      ││
│ └───────────────────────┘│
│                         │
│ A PROPOS                │
│ ┌───────────────────────┐│
│ │ Version 1.0.0         ││
│ │ Changelog         [>] ││
│ │ Support            [>] ││
│ └───────────────────────┘│
│                         │
│ ┌───────────────────────┐│
│ │   SE DECONNECTER      ││  ← Rouge
│ └───────────────────────┘│
│                         │
├─────────────────────────┤
│ 📊    💼    🎯   🤖   ⚙│
└─────────────────────────┘
```

### 3.13 Bottom Sheet : Vendre Maintenant

```
         ┌───────────────────────┐
         │         ───           │  ← Drag handle
         │                       │
         │  ⚠ VENDRE MAINTENANT  │
         │                       │
         │  BTC/USDT             │
         │  Quantite: 0.00148   │
         │  Prix actuel: $67,234│
         │  P&L estime: +$0.30  │
         │                       │
         │  Cette action va      │
         │  vendre votre BTC au  │
         │  prix du marche.      │
         │                       │
         │ ┌───────────────────┐ │
         │ │  CONFIRMER VENTE  │ │  ← Bouton rouge
         │ └───────────────────┘ │
         │                       │
         │ ┌───────────────────┐ │
         │ │     Annuler       │ │  ← Bouton outline
         │ └───────────────────┘ │
         └───────────────────────┘
```

### 3.14 Notification Push (Apparence)

```
┌─────────────────────────────────┐
│ ◆ KAIROS TRADING       10:23   │
│                                 │
│ 📈 BUY Execute - BTC/USDT     │
│ Prix: $67,234.50 | Qty: 0.0015 │
│ Strategie: Scalping Hard        │
│ SL: $66,225 (-1.5%)            │
│                                 │
│ [Voir]              [Ignorer]  │
└─────────────────────────────────┘
```

### 3.15 Animations et Transitions

| Element | Animation |
|---------|-----------|
| Changement prix | Flash vert (hausse) ou rouge (baisse) pendant 300ms |
| P&L | Counter animation (chiffres qui defilent) |
| Sparklines | Dessin progressif de gauche a droite |
| Navigation tabs | Cross-fade 200ms |
| Pull-to-refresh | Rotation spinner Kairos |
| Bottom sheets | Spring animation de bas en haut |
| Cartes | Fade-in + translateY au scroll |
| Trades | SlideInRight pour les nouveaux trades |
| Badges | Scale bounce quand la valeur change |
| Boutons | Haptic feedback (vibration legere) au tap |

---

## 4. Architecture Technique

### 4.1 Stack

```
React Native 0.76+ (New Architecture)
├── Expo SDK 52+         # Managed workflow pour simplifier le build
├── Expo Router          # File-based routing (comme Next.js)
├── NativeWind 4         # Tailwind CSS pour React Native
├── React Query 5        # Cache API + gestion des etats serveur
├── Zustand              # State management (leger, performant)
├── MMKV                 # Stockage local ultra-rapide (50x AsyncStorage)
├── socket.io-client     # WebSocket pour temps reel
├── Expo Notifications   # Push notifications (FCM + APNs)
├── Expo SecureStore     # Stockage securise (tokens)
├── react-native-wagmi-charts  # Graphiques financiers performants
├── react-native-reanimated    # Animations fluides 60fps
├── react-native-gesture-handler # Gestures (swipe, pinch)
├── expo-local-authentication  # Biometrie
└── Sentry               # Crash reporting
```

### 4.2 Architecture des Fichiers

```
mobile/
├── app/                        # Expo Router (file-based)
│   ├── _layout.tsx             # Root layout (providers, auth guard)
│   ├── index.tsx               # Redirect vers login ou tabs
│   ├── login.tsx               # Ecran login
│   │
│   ├── (tabs)/                 # Tab navigation (authentifie)
│   │   ├── _layout.tsx         # Tab bar layout
│   │   ├── index.tsx           # Overview (Tab 1)
│   │   ├── portfolio.tsx       # Portfolio (Tab 2)
│   │   ├── strategies.tsx      # Strategies (Tab 3)
│   │   ├── ai-agent.tsx        # Agent IA (Tab 4)
│   │   └── settings.tsx        # Settings (Tab 5)
│   │
│   ├── trade/
│   │   └── [id].tsx            # Detail d'un trade
│   │
│   ├── trades/
│   │   └── index.tsx           # Historique des trades
│   │
│   ├── alerts/
│   │   ├── index.tsx           # Liste alertes
│   │   └── create.tsx          # Creer alerte
│   │
│   ├── backtest/
│   │   ├── index.tsx           # Lancer backtest
│   │   └── [id].tsx            # Resultats backtest
│   │
│   ├── bot-control.tsx         # Controle du bot
│   │
│   └── settings/
│       ├── profile.tsx         # Editer profil
│       ├── notifications.tsx   # Config notifs
│       ├── security.tsx        # Biometrie, 2FA
│       └── sessions.tsx        # Sessions actives
│
├── components/                  # Composants reutilisables
│   ├── ui/                      # Composants de base
│   │   ├── Card.tsx
│   │   ├── Button.tsx
│   │   ├── Badge.tsx
│   │   ├── Input.tsx
│   │   ├── Toggle.tsx
│   │   ├── BottomSheet.tsx
│   │   ├── Skeleton.tsx        # Loading placeholders
│   │   └── EmptyState.tsx
│   │
│   ├── charts/                  # Graphiques
│   │   ├── Sparkline.tsx
│   │   ├── EquityCurve.tsx
│   │   ├── CandleChart.tsx
│   │   ├── DonutChart.tsx
│   │   └── PnLBar.tsx
│   │
│   ├── trading/                 # Composants metier
│   │   ├── PriceDisplay.tsx     # Prix avec flash animation
│   │   ├── PositionCard.tsx
│   │   ├── TradeRow.tsx
│   │   ├── StrategyCard.tsx
│   │   ├── KPICard.tsx
│   │   ├── AlertRow.tsx
│   │   └── ChatBubble.tsx
│   │
│   └── layout/
│       ├── Header.tsx
│       └── TabBar.tsx
│
├── services/                    # Logique metier
│   ├── api.ts                   # Client API (axios + interceptors)
│   ├── websocket.ts             # WebSocket manager (socket.io)
│   ├── notifications.ts         # Push notification handler
│   ├── auth.ts                  # Login, refresh, biometrie
│   └── cache.ts                 # MMKV cache strategies
│
├── stores/                      # Zustand stores
│   ├── useAuthStore.ts          # Token, user, isAuthenticated
│   ├── useMarketStore.ts        # Prix, bougies (WebSocket)
│   ├── useTradingStore.ts       # Positions, trades
│   └── useSettingsStore.ts      # Preferences locales
│
├── hooks/                       # Custom hooks
│   ├── useWebSocket.ts          # Connexion/reconnexion WS
│   ├── useBiometrics.ts         # Face ID / empreinte
│   ├── useAutoLock.ts           # Verrouillage auto
│   ├── useRefreshOnFocus.ts     # Refresh quand l'app revient au premier plan
│   └── usePushPermission.ts     # Demande permission push
│
├── types/                       # TypeScript types
│   ├── api.ts                   # Types API (Trade, Strategy, etc.)
│   ├── navigation.ts            # Types de navigation
│   └── websocket.ts             # Events WebSocket
│
├── utils/
│   ├── format.ts                # Formatage prix, dates, %
│   ├── colors.ts                # Palette de couleurs
│   └── haptics.ts               # Retour haptique
│
├── constants/
│   ├── theme.ts                 # Design tokens
│   └── config.ts                # API URL, timeouts
│
├── assets/
│   ├── icon.png                 # Icone app (1024x1024)
│   ├── splash.png               # Splash screen
│   ├── adaptive-icon.png        # Android adaptive icon
│   └── fonts/
│       ├── Inter-*.ttf
│       └── JetBrainsMono-*.ttf
│
├── app.json                     # Config Expo
├── eas.json                     # Config EAS Build
├── package.json
└── tsconfig.json
```

### 4.3 Flux de Donnees

```
┌─────────────────────────────────────────────┐
│                  APP MOBILE                  │
│                                             │
│  ┌──────────┐    ┌────────────┐             │
│  │ Zustand   │◄──│ React Query│             │
│  │ Stores    │    │ Cache      │             │
│  │ (state)   │    │ (server)   │             │
│  └─────┬────┘    └──────┬─────┘             │
│        │                │                    │
│        ▼                ▼                    │
│  ┌──────────────────────────┐               │
│  │     React Components     │               │
│  │    (UI reacts to state)  │               │
│  └──────────────────────────┘               │
│        ▲                ▲                    │
│        │                │                    │
│  ┌─────┴────┐    ┌──────┴─────┐             │
│  │WebSocket │    │ REST API   │             │
│  │(realtime)│    │ (actions)  │             │
│  └─────┬────┘    └──────┬─────┘             │
└────────┼────────────────┼───────────────────┘
         │                │
         ▼                ▼
   ┌──────────────────────────┐
   │      KAIROS API          │
   │   (FastAPI + WebSocket)  │
   └──────────────────────────┘
```

### 4.4 Gestion du WebSocket

```typescript
// services/websocket.ts - Singleton
class KairosWebSocket {
  private socket: Socket;
  private reconnectAttempts = 0;
  private maxReconnect = 10;

  connect(token: string) {
    this.socket = io(API_WS_URL, {
      auth: { token },
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 30000,
    });

    // Evenements recus
    this.socket.on('price_update', (data) => {
      useMarketStore.getState().updatePrice(data);
    });

    this.socket.on('position_update', (data) => {
      useTradingStore.getState().updatePosition(data);
    });

    this.socket.on('new_trade', (data) => {
      useTradingStore.getState().addTrade(data);
    });

    this.socket.on('signal', (data) => {
      // Flash notification in-app
    });

    this.socket.on('bot_status', (data) => {
      useTradingStore.getState().updateBotStatus(data);
    });
  }

  disconnect() { ... }
  subscribe(pairs: string[]) { ... }
  unsubscribe(pairs: string[]) { ... }
}
```

### 4.5 Gestion de l'Authentification

```
FLOW AUTH
━━━━━━━━━━━━━━━━━━

1. Premier lancement
   → Ecran login
   → Saisie email + password
   → POST /api/auth/login
   → Recevoir access_token (15min) + refresh_token (7j)
   → Stocker dans SecureStore (chiffre)
   → Proposer d'activer la biometrie

2. Lancement suivant (biometrie active)
   → Ecran biometrie (Face ID / empreinte)
   → Si succes → charger tokens depuis SecureStore
   → Si access_token expire → POST /api/auth/refresh
   → Si refresh_token expire → Ecran login

3. Auto-lock (app en arriere-plan > 5min)
   → Ecran biometrie au retour
   → Tokens toujours valides (pas de re-login)

4. Logout
   → POST /api/auth/logout (invalider refresh_token)
   → Supprimer SecureStore
   → Supprimer cache MMKV
   → Retour ecran login
```

---

## 5. Navigation et Ecrans

### 5.1 Arbre de Navigation

```
Root
├── Login (non-authentifie)
│
├── (tabs) (authentifie)
│   ├── Overview            ← Tab 1 (icone: graphique)
│   ├── Portfolio            ← Tab 2 (icone: mallette)
│   ├── Strategies          ← Tab 3 (icone: cible)
│   ├── Agent IA            ← Tab 4 (icone: robot)
│   └── Settings            ← Tab 5 (icone: engrenage)
│
├── Stacks (depuis les tabs)
│   ├── Trades (liste)       ← Depuis Overview
│   ├── Trade Detail [id]    ← Depuis Trades ou Overview
│   ├── Alerts               ← Depuis Settings ou Header
│   ├── Alert Create         ← Depuis Alerts
│   ├── Bot Control          ← Depuis Overview ou Settings
│   ├── Backtest             ← Depuis Strategies
│   ├── Backtest Result [id] ← Depuis Backtest
│   ├── Profile Edit         ← Depuis Settings
│   ├── Notifications Config ← Depuis Settings
│   ├── Security             ← Depuis Settings
│   └── Sessions             ← Depuis Security
│
└── Modals / Bottom Sheets
    ├── Sell Confirmation     ← Depuis Position Card
    ├── Activate Strategy     ← Depuis Strategy Card
    ├── Bot Mode Change       ← Depuis Bot Control
    └── Notification Detail   ← Depuis notification push
```

### 5.2 Tab Bar

```
┌────────┬────────┬────────┬────────┬────────┐
│   📊   │   💼   │   🎯   │   🤖   │   ⚙    │
│  Home  │ Portf. │ Strat. │  IA    │ Param. │
└────────┴────────┴────────┴────────┴────────┘

Style:
  - Background: #1E2329
  - Active icon: #F0B90B (or)
  - Inactive icon: #5E6673 (gris)
  - Active label: #EAECEF
  - Inactive label: #5E6673
  - Border top: 1px #2B3139
  - Height: 56px (iOS) / 60px (Android)
  - Badge notification: #F6465D (rouge) avec count
```

### 5.3 Liste Exhaustive des Ecrans

| # | Ecran | Route | Type |
|---|-------|-------|------|
| 1 | Splash | `/` | Redirect |
| 2 | Login | `/login` | Stack |
| 3 | Overview | `/(tabs)/` | Tab |
| 4 | Portfolio | `/(tabs)/portfolio` | Tab |
| 5 | Strategies | `/(tabs)/strategies` | Tab |
| 6 | Agent IA | `/(tabs)/ai-agent` | Tab |
| 7 | Settings | `/(tabs)/settings` | Tab |
| 8 | Historique Trades | `/trades` | Stack |
| 9 | Detail Trade | `/trade/[id]` | Stack |
| 10 | Alertes | `/alerts` | Stack |
| 11 | Creer Alerte | `/alerts/create` | Stack |
| 12 | Controle Bot | `/bot-control` | Stack |
| 13 | Backtest | `/backtest` | Stack |
| 14 | Resultat Backtest | `/backtest/[id]` | Stack |
| 15 | Editer Profil | `/settings/profile` | Stack |
| 16 | Config Notifications | `/settings/notifications` | Stack |
| 17 | Securite | `/settings/security` | Stack |
| 18 | Sessions | `/settings/sessions` | Stack |
| 19 | Rapports IA | `/ai-reports` | Stack |
| 20 | Detail Rapport | `/ai-reports/[id]` | Stack |

---

## 6. Notifications Push

### 6.1 Architecture

```
Evenement (Engine/API)
        │
        ▼
  Kairos Notifier Service
        │
        ├── Telegram Bot API
        │
        └── Firebase Cloud Messaging (FCM)
                │
                ├── Android (FCM direct)
                │
                └── iOS (FCM → APNs)
                        │
                        ▼
                   App Mobile
                        │
                  ┌─────┴─────┐
                  │ Foreground │ → In-app toast/banner
                  │ Background │ → System notification
                  │ Killed     │ → System notification
                  └───────────┘
```

### 6.2 Types de Notifications

| Type | Categorie | Priorite | Son | Vibre | Exemple |
|------|-----------|----------|-----|-------|---------|
| `trade_buy` | Trading | Haute | Oui | Oui | "BUY BTC $67,234 - Scalping Hard" |
| `trade_sell_profit` | Trading | Haute | Oui | Oui | "SELL BTC +0.60% (+$0.40)" |
| `trade_sell_loss` | Trading | Haute | Oui | Oui | "SELL BTC -0.32% (-$0.21) SL" |
| `stop_loss` | Urgence | Critique | Oui | Long | "STOP-LOSS BTC -1.5%" |
| `trailing_activated` | Info | Normale | Non | Non | "Trailing active BTC +0.6%" |
| `alert_triggered` | Alerte | Haute | Oui | Oui | "BTC > $68,000 !" |
| `bot_error` | Systeme | Critique | Oui | Long | "Bot erreur: connexion perdue" |
| `bot_stopped` | Systeme | Haute | Oui | Oui | "Bot arrete" |
| `bot_started` | Systeme | Normale | Non | Oui | "Bot demarre - Scalping Hard" |
| `drawdown_warning` | Risque | Critique | Oui | Long | "Drawdown -5% - limite atteinte" |
| `report_ready` | Info | Basse | Non | Non | "Rapport IA disponible" |
| `daily_summary` | Info | Basse | Non | Non | "Recap: 3 trades, +$1.85" |

### 6.3 Canaux de Notification (Android)

```
CHANNELS ANDROID
━━━━━━━━━━━━━━━━━

kairos_trading      : Trades (BUY/SELL)     - Importance HIGH
kairos_alerts       : Alertes utilisateur   - Importance HIGH
kairos_system       : Bot status, erreurs   - Importance DEFAULT
kairos_risk         : Drawdown, SL critique - Importance MAX
kairos_reports      : Rapports, recaps      - Importance LOW
```

### 6.4 Actions depuis la Notification

| Notification | Action au tap | Deep link |
|-------------|---------------|-----------|
| Trade BUY | Ouvre Overview → position | `kairos://tabs` |
| Trade SELL | Ouvre Detail Trade | `kairos://trade/{id}` |
| Alerte | Ouvre Alertes | `kairos://alerts` |
| Bot erreur | Ouvre Bot Control | `kairos://bot-control` |
| Rapport | Ouvre Rapport IA | `kairos://ai-reports/{id}` |
| Daily summary | Ouvre Overview | `kairos://tabs` |

### 6.5 Payload Push

```json
{
  "notification": {
    "title": "📈 BUY Execute",
    "body": "BTC/USDT @ $67,234 | Scalping Hard"
  },
  "data": {
    "type": "trade_buy",
    "trade_id": "47",
    "pair": "BTCUSDT",
    "price": "67234.50",
    "strategy": "Scalping Hard",
    "deep_link": "kairos://trade/47"
  },
  "android": {
    "priority": "high",
    "notification": {
      "channel_id": "kairos_trading",
      "color": "#0ECB81"
    }
  },
  "apns": {
    "payload": {
      "aps": {
        "sound": "trade.aiff",
        "badge": 1,
        "category": "TRADE"
      }
    }
  }
}
```

---

## 7. Mode Offline

### 7.1 Strategie de Cache

| Donnee | Stockage | TTL | Strategie |
|--------|----------|-----|-----------|
| Prix actuel | Zustand (RAM) | 0 (live) | Stale-while-revalidate |
| Positions | MMKV | 1 min | Cache-first, background refresh |
| Trades recents (50) | MMKV | 15 min | Cache-first |
| Trades historique | React Query cache | 5 min | Stale-while-revalidate |
| Strategies | MMKV | 1h | Cache-first |
| Stats | MMKV | 15 min | Cache-first |
| Config bot | MMKV | 30 min | Cache-first |
| Profil user | MMKV | 24h | Cache-first |
| Tokens | SecureStore | 7j (refresh) | Persiste |
| Preferences | MMKV | Illimite | Local-only |

### 7.2 Comportement Offline

```
ONLINE                        OFFLINE
━━━━━━━                       ━━━━━━━

WebSocket connecte            WebSocket deconnecte
Prix temps reel               Dernier prix cache + timestamp
Positions live                Dernieres positions + "⚠ hors-ligne"
Actions disponibles           Actions desactivees (boutons gris)
Pull-to-refresh OK            Pull-to-refresh → erreur + cache
Chat IA actif                 Chat IA desactive
Logs temps reel               Logs caches
```

### 7.3 Indicateur de Connexion

```
┌─────────────────────────┐
│ ⚠ Hors-ligne            │  ← Bandeau jaune en haut
│ Dernieres donnees: 2min │
└─────────────────────────┘
```

Apparait quand :
- WebSocket deconnecte depuis > 10 secondes
- Aucune reponse API depuis > 30 secondes
- Mode avion detecte

---

## 8. Securite

### 8.1 Stockage

| Donnee | Stockage | Chiffrement |
|--------|----------|-------------|
| Access token | SecureStore | Keychain (iOS) / Keystore (Android) |
| Refresh token | SecureStore | Keychain / Keystore |
| Preferences | MMKV | Non (pas sensible) |
| Cache trades | MMKV | Non (pas sensible) |
| PIN / biometrie | SecureStore | Hardware-backed |

### 8.2 Protections

| Protection | Implementation |
|------------|----------------|
| Certificate pinning | Vérification du certificat SSL du serveur |
| Jailbreak/root detection | `expo-device` + checks manuels |
| Screenshot prevention | `FLAG_SECURE` (Android) sur ecrans sensibles |
| Clipboard auto-clear | Vide le presse-papier apres copie de donnees sensibles |
| Biometrie | Face ID / Touch ID / Empreinte pour deverrouiller |
| Auto-lock | Verrouillage apres N minutes en arriere-plan |
| Token rotation | Refresh token a usage unique avec rotation |
| App Transport Security | HTTPS enforce (iOS) |
| Network Security Config | HTTPS enforce (Android) |
| Code obfuscation | Hermes engine (bytecode) + ProGuard |
| No logging in production | Aucun `console.log` avec donnees sensibles |

### 8.3 Controles Sensibles

Actions necessitant une confirmation supplementaire :

| Action | Confirmation |
|--------|-------------|
| Vendre maintenant | Bottom sheet + bouton confirmer |
| Activer strategie | Dialog confirmation |
| Mode DRY→LIVE | Double confirmation + biometrie obligatoire |
| Arreter le bot | Dialog confirmation |
| Se deconnecter | Dialog confirmation |
| Supprimer compte | Saisie du mot de passe + Dialog |

---

## 9. Performance

### 9.1 Objectifs

| Metrique | Cible | Outil de mesure |
|----------|-------|-----------------|
| Cold start | < 2s | Flashlight |
| TTI (time to interactive) | < 3s | React Native Performance |
| FPS navigation | 60 fps | Flipper |
| FPS scrolling | 60 fps | Flipper |
| Taille APK | < 30 MB | EAS Build |
| Taille IPA | < 50 MB | EAS Build |
| RAM usage | < 150 MB | Instruments / Android Profiler |
| Battery drain | < 3%/h en foreground | Battery stats OS |

### 9.2 Optimisations

| Technique | Description |
|-----------|-------------|
| Hermes engine | JavaScript bytecode pre-compile (cold start -50%) |
| Lazy loading | Ecrans charges a la demande (pas au lancement) |
| FlashList | Remplacement de FlatList (performance listes longues) |
| Image caching | `expo-image` avec cache disque |
| Memo/useMemo | Eviter les re-renders inutiles |
| WebSocket batching | Grouper les updates de prix (max 1 update/500ms) |
| Skeleton screens | Afficher des placeholders pendant le chargement |
| React Query | Deduplication des requetes, cache intelligent |
| Reanimated | Animations sur le thread natif (pas JS) |
| Avoid re-renders | `React.memo`, selecteurs Zustand fins |

### 9.3 Gestion Batterie

```
FOREGROUND (app visible)
  WebSocket: connecte, updates toutes les 500ms
  Refresh: toutes les 30s
  Animations: actives

BACKGROUND (app en arriere-plan)
  WebSocket: deconnecte apres 30s
  Refresh: aucun (rely on push notifications)
  Taches: aucune

NOTIFICATION RECUE EN BACKGROUND
  Wake up minimal pour afficher la notification
  Pas de fetch de donnees supplementaires
```

---

## 10. Publication Stores

### 10.1 App Store (iOS)

| Element | Valeur |
|---------|--------|
| Nom | Kairos Trading |
| Sous-titre | Bot de Trading BTC Automatise |
| Categorie | Finance |
| Sous-categorie | - |
| Prix | Gratuit |
| In-App Purchases | Non (pour le moment) |
| Langues | Francais, Anglais |
| Age rating | 17+ (trading financier) |
| Privacy | Politique de confidentialite requise |

**Guidelines a respecter :**
- Pas de contenu trompeur ("gagner de l'argent facilement")
- Mention claire des risques financiers
- Pas de crypto mining
- L'app doit fonctionner sans creation de compte (mode demo) ← recommande
- Privacy Policy et Terms of Service accessibles

### 10.2 Google Play (Android)

| Element | Valeur |
|---------|--------|
| Nom | Kairos Trading - Bot BTC |
| Categorie | Finance |
| Classification | Contenu PEGI 18 |
| Prix | Gratuit |
| Pays | Tous (sauf pays restreints pour le crypto) |
| Langues | Francais, Anglais |

**Compliance :**
- Google Play Financial Services Policy
- Data Safety section remplie
- Pas de permissions excessives
- Signing avec Play App Signing

### 10.3 Assets Necessaires

| Asset | Taille | Format |
|-------|--------|--------|
| App Icon | 1024x1024 | PNG (pas de transparence iOS) |
| Adaptive Icon (Android) | 512x512 (foreground) + background | PNG |
| Splash Screen | 1284x2778 (iPhone 15 Pro Max) | PNG |
| Screenshots iPhone 6.7" | 1290x2796 | PNG (min 3, max 10) |
| Screenshots iPhone 6.5" | 1284x2778 | PNG |
| Screenshots iPad 12.9" | 2048x2732 | PNG (si iPad) |
| Screenshots Android Phone | 1080x1920 | PNG (min 2, max 8) |
| Feature Graphic (Android) | 1024x500 | PNG |
| App Preview Video | 30s max, 1080p | MP4 (optionnel) |

### 10.4 Build et Distribution

```
EAS BUILD (Expo Application Services)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Profils de build (eas.json)

development:
  - Distribution: internal
  - Debug: true
  - Usage: tests sur device

preview:
  - Distribution: internal
  - Debug: false
  - Usage: TestFlight / Internal Testing

production:
  - Distribution: store
  - Debug: false
  - Usage: App Store / Play Store

# Commandes

eas build --platform all --profile production
eas submit --platform ios
eas submit --platform android
```

### 10.5 Versioning

```
Format: MAJOR.MINOR.PATCH (Semantic Versioning)

1.0.0  - Lancement initial
1.1.0  - Ajout backtest mobile
1.2.0  - Ajout chat vocal IA
2.0.0  - Multi-exchange, copy-trading

Build number: incrementé a chaque submission
  iOS: 1, 2, 3, ...
  Android: versionCode 1, 2, 3, ...
```

---

## 11. Testing

### 11.1 Strategie

| Type | Outil | Couverture |
|------|-------|------------|
| Unit tests | Jest + React Native Testing Library | 70% composants |
| Integration tests | Jest + MSW (mock API) | Flows principaux |
| E2E tests | Maestro (recommande) ou Detox | 5 flows critiques |
| Visual regression | Storybook + Chromatic (optionnel) | Composants UI |
| Performance | Flashlight | Cold start, FPS |
| Manual QA | TestFlight + Internal Testing | Avant chaque release |

### 11.2 Flows E2E Critiques

```
1. LOGIN FLOW
   Login → biometrie → Overview charge → prix affiche

2. TRADE MONITORING
   Overview → voir position → P&L se met a jour → tap trade → detail

3. SELL FLOW
   Position card → "Vendre maintenant" → bottom sheet → confirmer → position fermee

4. STRATEGY ACTIVATION
   Strategies → tap strategie → "Activer" → confirmer → badge "Active"

5. ALERT CREATION
   Alertes → "+" → remplir → creer → apparait dans la liste
```

### 11.3 Devices de Test

| OS | Device | Priorite |
|----|--------|----------|
| iOS 17+ | iPhone 15 Pro | Haute |
| iOS 16 | iPhone 13 | Moyenne |
| Android 14 | Pixel 8 | Haute |
| Android 12 | Samsung Galaxy S21 | Moyenne |
| Android 11 | Xiaomi Redmi Note | Basse |

---

## 12. Estimation

### Phase 1 : Setup + Core (1 semaine)

| Tache | Effort |
|-------|--------|
| Init projet Expo + config | 0.5j |
| Design system (theme, composants UI) | 1j |
| Auth (login, biometrie, token management) | 1j |
| Navigation (tabs + stacks) | 0.5j |
| Service API (axios + interceptors) | 0.5j |
| WebSocket service | 0.5j |
| Stores Zustand | 0.5j |

### Phase 2 : Ecrans Principaux (2 semaines)

| Tache | Effort |
|-------|--------|
| Overview (dashboard) | 2j |
| Portfolio | 1.5j |
| Historique Trades + Detail | 1.5j |
| Strategies (liste + detail) | 1j |
| Agent IA (chat) | 2j |
| Settings (tous les sous-ecrans) | 1.5j |

### Phase 3 : Features Avancees (1 semaine)

| Tache | Effort |
|-------|--------|
| Alertes (liste + creation) | 1j |
| Bot Control | 1j |
| Backtest (lancement + resultats) | 1.5j |
| Push notifications (FCM setup + handlers) | 1j |
| Mode offline (cache MMKV) | 0.5j |

### Phase 4 : Polish + Publication (1 semaine)

| Tache | Effort |
|-------|--------|
| Animations et transitions | 1j |
| Tests E2E (5 flows) | 1j |
| Assets stores (screenshots, descriptions) | 0.5j |
| Build production + soumission | 0.5j |
| Bug fixes et polish | 2j |

**Total estime : 5-6 semaines** (1 developpeur)

### Timeline

```
Semaine 1  : Setup + Auth + Navigation + Services
Semaine 2  : Overview + Portfolio + Trades
Semaine 3  : Strategies + Agent IA + Settings
Semaine 4  : Alertes + Bot Control + Backtest + Push
Semaine 5  : Polish + Tests + Assets
Semaine 6  : Soumission stores + corrections review
```

---

## Annexe : Checklist Pre-Submission

### iOS (App Store Connect)

- [ ] Privacy Policy URL
- [ ] Terms of Service URL
- [ ] App Icon 1024x1024 (pas de transparence)
- [ ] Screenshots 6.7" et 6.5"
- [ ] Description (max 4000 chars)
- [ ] Keywords (max 100 chars)
- [ ] Age rating questionnaire rempli
- [ ] Data collection disclosure
- [ ] Sign in with Apple (si autres SSO)
- [ ] Export compliance (chiffrement)

### Android (Google Play Console)

- [ ] Feature Graphic 1024x500
- [ ] Screenshots min 2
- [ ] Short description (max 80 chars)
- [ ] Full description (max 4000 chars)
- [ ] Content rating questionnaire
- [ ] Data Safety form
- [ ] Target audience declaration
- [ ] Financial features declaration
- [ ] App signing configured
- [ ] Internal testing track validated

---

*Kairos Trading Mobile - Cahier des charges v1.0 - Fevrier 2026*
*A realiser apres la mise en production du bot et de l'API Kairos.*
