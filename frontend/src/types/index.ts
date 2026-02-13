// ─── Auth ─────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse {
  tokens: TokenPair;
  user: User;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  username: string;
}

// ─── Trades ───────────────────────────────────────────────────
export interface Trade {
  id: string;
  pair: string;
  side: "BUY" | "SELL";
  entry_price: number;
  exit_price: number | null;
  quantity: number;
  entry_time: string;
  exit_time: string | null;
  pnl_usdt: number;
  pnl_pct: number;
  fees: number;
  strategy_name: string;
  entry_reason: string;
  exit_reason: string;
  status: "OPEN" | "CLOSED" | "CANCELLED";
  metadata_json: string | null;
}

export interface TradeListResponse {
  total: number;
  page: number;
  per_page: number;
  pages: number;
  trades: Trade[];
}

export interface TradeStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl_usdt: number;
  total_pnl_pct: number;
  average_pnl_usdt: number;
  max_win_usdt: number;
  max_loss_usdt: number;
  average_duration_minutes: number;
  profit_factor: number;
  sharpe_ratio: number | null;
}

export interface TradeJournal {
  id: number;
  trade_id: number;
  notes: string;
  tags: string[];
  rating: number | null;
  created_at: string;
  updated_at: string | null;
}

// ─── Strategies ───────────────────────────────────────────────
export interface Condition {
  indicator: string;
  params: Record<string, unknown>;
  operator: string;
  value: number | string | null;
}

export interface Filter {
  type: string;
  params: Record<string, unknown>;
  enabled: boolean;
}

export interface RiskConfig {
  stop_loss_pct?: number;
  trailing_activation_pct?: number;
  trailing_distance_pct?: number;
  take_profit_levels?: Array<Record<string, number>>;
  max_position_size_pct?: number;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  version: string;
  pairs: string[];
  timeframe: string;
  entry_conditions: Condition[];
  exit_conditions: Condition[];
  filters: Filter[];
  risk: RiskConfig;
  indicators_needed: string[];
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string | null;
}

export interface StrategyListResponse {
  total: number;
  strategies: Strategy[];
}

export interface StrategyValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

// ─── Bot ──────────────────────────────────────────────────────
export interface BotStatus {
  running: boolean;
  uptime_seconds: number;
  pairs_active: string[];
  open_positions: number;
  last_signal_time: string | null;
  mode: "dry_run" | "live";
  version: string;
  strategy: string;
  daily_trades: number;
  daily_pnl_usdt: number;
  trust_level: string;
  circuit_breaker: boolean;
}

export interface BotConfig {
  dry_run: boolean;
  pairs: string[];
  strategy_type: string;
  ha_timeframe: string;
  entry_timeframe: string;
  stop_loss_pct: number;
  trailing_activation_pct: number;
  trailing_distance_pct: number;
  use_full_balance: boolean;
  trade_capital_usdt: number;
  telegram_enabled: boolean;
}

// ─── Market ───────────────────────────────────────────────────
export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Ticker {
  pair: string;
  price: number;
  high_24h: number;
  low_24h: number;
  volume_24h: number;
  change_24h_pct: number;
}

// ─── Portfolio ────────────────────────────────────────────────
export interface Position {
  pair: string;
  side: "LONG" | "SHORT";
  entry_price: number;
  current_price: number;
  quantity: number;
  pnl_usdt: number;
  pnl_pct: number;
  stop_loss: number | null;
  take_profit: number | null;
  strategy_name: string;
  entry_time: string;
}

export interface PortfolioOverview {
  total_value_usdt: number;
  available_usdt: number;
  in_positions_usdt: number;
  exposure_pct: number;
  positions: Position[];
  daily_pnl_usdt: number;
  daily_pnl_pct: number;
}

// ─── Common ───────────────────────────────────────────────────
export interface SuccessResponse {
  success: boolean;
  message: string;
  data?: unknown;
}

export interface ErrorResponse {
  success: boolean;
  error: string;
  detail?: string;
}
