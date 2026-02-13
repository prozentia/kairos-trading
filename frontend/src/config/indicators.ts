// Catalog of all 27 Kairos Trading indicators with params and operators.

export type ParamType = "number" | "select" | "string";

export interface ParamDef {
  key: string;
  label: string;
  type: ParamType;
  default: number | string;
  options?: string[]; // For select type
  min?: number;
  max?: number;
  step?: number;
}

export interface OpDef {
  key: string;
  label: string;
  needsValue: boolean;
}

export type IndicatorCategory = "trend" | "momentum" | "volatility" | "volume" | "special";

export interface IndicatorDef {
  key: string;
  name: string;
  category: IndicatorCategory;
  params: ParamDef[];
  operators: OpDef[];
}

// Category labels for display
export const CATEGORY_LABELS: Record<IndicatorCategory, string> = {
  trend: "Tendance",
  momentum: "Momentum",
  volatility: "Volatilite",
  volume: "Volume",
  special: "Special",
};

export const INDICATORS: IndicatorDef[] = [
  // =====================================================================
  // TREND (8)
  // =====================================================================
  {
    key: "ema",
    name: "EMA",
    category: "trend",
    params: [
      { key: "period", label: "Period", type: "number", default: 20, min: 2, max: 500 },
      { key: "source", label: "Source", type: "select", default: "close", options: ["open", "high", "low", "close"] },
    ],
    operators: [
      { key: "price_above", label: "Prix au-dessus", needsValue: false },
      { key: "price_below", label: "Prix en-dessous", needsValue: false },
      { key: "rising", label: "En hausse", needsValue: false },
      { key: "falling", label: "En baisse", needsValue: false },
    ],
  },
  {
    key: "sma",
    name: "SMA",
    category: "trend",
    params: [
      { key: "period", label: "Period", type: "number", default: 20, min: 2, max: 500 },
      { key: "source", label: "Source", type: "select", default: "close", options: ["open", "high", "low", "close"] },
    ],
    operators: [
      { key: "price_above", label: "Prix au-dessus", needsValue: false },
      { key: "price_below", label: "Prix en-dessous", needsValue: false },
      { key: "rising", label: "En hausse", needsValue: false },
      { key: "falling", label: "En baisse", needsValue: false },
    ],
  },
  {
    key: "ema_cross",
    name: "EMA Crossover",
    category: "trend",
    params: [
      { key: "fast_period", label: "Fast EMA", type: "number", default: 9, min: 2, max: 200 },
      { key: "slow_period", label: "Slow EMA", type: "number", default: 21, min: 2, max: 500 },
    ],
    operators: [
      { key: "golden_cross", label: "Golden Cross", needsValue: false },
      { key: "death_cross", label: "Death Cross", needsValue: false },
      { key: "bullish", label: "Haussier (fast > slow)", needsValue: false },
      { key: "bearish", label: "Baissier (fast < slow)", needsValue: false },
    ],
  },
  {
    key: "donchian",
    name: "Donchian Channel",
    category: "trend",
    params: [
      { key: "period", label: "Period", type: "number", default: 20, min: 5, max: 200 },
    ],
    operators: [
      { key: "break_upper", label: "Cassure haut", needsValue: false },
      { key: "break_lower", label: "Cassure bas", needsValue: false },
      { key: "inside", label: "A l'interieur", needsValue: false },
      { key: "squeeze", label: "Compression", needsValue: false },
    ],
  },
  {
    key: "heikin_ashi",
    name: "Heikin-Ashi",
    category: "trend",
    params: [],
    operators: [
      { key: "is_green", label: "Bougie verte", needsValue: false },
      { key: "is_red", label: "Bougie rouge", needsValue: false },
      { key: "flip_to_green", label: "Retournement vert", needsValue: false },
      { key: "flip_to_red", label: "Retournement rouge", needsValue: false },
      { key: "consecutive_green", label: "Vertes consecutives", needsValue: true },
      { key: "consecutive_red", label: "Rouges consecutives", needsValue: true },
    ],
  },
  {
    key: "ichimoku",
    name: "Ichimoku",
    category: "trend",
    params: [
      { key: "tenkan", label: "Tenkan", type: "number", default: 9, min: 2, max: 100 },
      { key: "kijun", label: "Kijun", type: "number", default: 26, min: 2, max: 200 },
      { key: "senkou_b", label: "Senkou B", type: "number", default: 52, min: 2, max: 200 },
    ],
    operators: [
      { key: "above_cloud", label: "Au-dessus du nuage", needsValue: false },
      { key: "below_cloud", label: "En-dessous du nuage", needsValue: false },
      { key: "in_cloud", label: "Dans le nuage", needsValue: false },
      { key: "tk_cross_up", label: "TK Cross haussier", needsValue: false },
      { key: "tk_cross_down", label: "TK Cross baissier", needsValue: false },
      { key: "cloud_green", label: "Nuage vert", needsValue: false },
      { key: "cloud_red", label: "Nuage rouge", needsValue: false },
    ],
  },
  {
    key: "supertrend",
    name: "Supertrend",
    category: "trend",
    params: [
      { key: "period", label: "ATR Period", type: "number", default: 10, min: 2, max: 100 },
      { key: "multiplier", label: "Multiplier", type: "number", default: 3.0, min: 0.5, max: 10, step: 0.1 },
    ],
    operators: [
      { key: "uptrend", label: "Tendance haussiere", needsValue: false },
      { key: "downtrend", label: "Tendance baissiere", needsValue: false },
      { key: "flip_up", label: "Retournement haussier", needsValue: false },
      { key: "flip_down", label: "Retournement baissier", needsValue: false },
    ],
  },
  {
    key: "parabolic_sar",
    name: "Parabolic SAR",
    category: "trend",
    params: [
      { key: "af_start", label: "AF Start", type: "number", default: 0.02, min: 0.01, max: 0.1, step: 0.01 },
      { key: "af_step", label: "AF Step", type: "number", default: 0.02, min: 0.01, max: 0.1, step: 0.01 },
      { key: "af_max", label: "AF Max", type: "number", default: 0.2, min: 0.1, max: 0.5, step: 0.01 },
    ],
    operators: [
      { key: "bullish", label: "Haussier (SAR sous prix)", needsValue: false },
      { key: "bearish", label: "Baissier (SAR sur prix)", needsValue: false },
      { key: "flip_up", label: "Retournement haussier", needsValue: false },
      { key: "flip_down", label: "Retournement baissier", needsValue: false },
    ],
  },

  // =====================================================================
  // MOMENTUM (7)
  // =====================================================================
  {
    key: "rsi",
    name: "RSI",
    category: "momentum",
    params: [
      { key: "period", label: "Period", type: "number", default: 14, min: 2, max: 100 },
    ],
    operators: [
      { key: "above", label: "Au-dessus de", needsValue: true },
      { key: "below", label: "En-dessous de", needsValue: true },
      { key: "cross_up", label: "Croise au-dessus de", needsValue: true },
      { key: "cross_down", label: "Croise en-dessous de", needsValue: true },
      { key: "rising", label: "En hausse", needsValue: false },
      { key: "falling", label: "En baisse", needsValue: false },
    ],
  },
  {
    key: "macd",
    name: "MACD",
    category: "momentum",
    params: [
      { key: "fast_period", label: "Fast", type: "number", default: 12, min: 2, max: 100 },
      { key: "slow_period", label: "Slow", type: "number", default: 26, min: 2, max: 200 },
      { key: "signal_period", label: "Signal", type: "number", default: 9, min: 2, max: 50 },
    ],
    operators: [
      { key: "cross_above_signal", label: "Croise au-dessus signal", needsValue: false },
      { key: "cross_below_signal", label: "Croise en-dessous signal", needsValue: false },
      { key: "above_zero", label: "Au-dessus de zero", needsValue: false },
      { key: "below_zero", label: "En-dessous de zero", needsValue: false },
      { key: "histogram_positive", label: "Histogramme positif", needsValue: false },
      { key: "histogram_negative", label: "Histogramme negatif", needsValue: false },
      { key: "histogram_rising", label: "Histogramme en hausse", needsValue: false },
      { key: "histogram_falling", label: "Histogramme en baisse", needsValue: false },
    ],
  },
  {
    key: "cci",
    name: "CCI",
    category: "momentum",
    params: [
      { key: "period", label: "Period", type: "number", default: 20, min: 5, max: 100 },
    ],
    operators: [
      { key: "above", label: "Au-dessus de", needsValue: true },
      { key: "below", label: "En-dessous de", needsValue: true },
      { key: "overbought", label: "Surachat (>100)", needsValue: false },
      { key: "oversold", label: "Survente (<-100)", needsValue: false },
      { key: "cross_up", label: "Croise au-dessus de", needsValue: true },
      { key: "cross_down", label: "Croise en-dessous de", needsValue: true },
    ],
  },
  {
    key: "roc",
    name: "ROC",
    category: "momentum",
    params: [
      { key: "period", label: "Period", type: "number", default: 12, min: 1, max: 100 },
    ],
    operators: [
      { key: "above", label: "Au-dessus de", needsValue: true },
      { key: "below", label: "En-dessous de", needsValue: true },
      { key: "positive", label: "Positif", needsValue: false },
      { key: "negative", label: "Negatif", needsValue: false },
      { key: "rising", label: "En hausse", needsValue: false },
      { key: "falling", label: "En baisse", needsValue: false },
    ],
  },
  {
    key: "stochastic",
    name: "Stochastic",
    category: "momentum",
    params: [
      { key: "k_period", label: "%K Period", type: "number", default: 14, min: 2, max: 100 },
      { key: "d_period", label: "%D Period", type: "number", default: 3, min: 2, max: 20 },
      { key: "smooth", label: "Smooth", type: "number", default: 3, min: 1, max: 10 },
    ],
    operators: [
      { key: "overbought", label: "Surachat", needsValue: true },
      { key: "oversold", label: "Survente", needsValue: true },
      { key: "cross_up", label: "%K croise au-dessus %D", needsValue: false },
      { key: "cross_down", label: "%K croise en-dessous %D", needsValue: false },
    ],
  },
  {
    key: "stochastic_rsi",
    name: "Stochastic RSI",
    category: "momentum",
    params: [
      { key: "rsi_period", label: "RSI Period", type: "number", default: 14, min: 2, max: 100 },
      { key: "stoch_period", label: "Stoch Period", type: "number", default: 14, min: 2, max: 100 },
      { key: "k_smooth", label: "K Smooth", type: "number", default: 3, min: 1, max: 10 },
      { key: "d_smooth", label: "D Smooth", type: "number", default: 3, min: 1, max: 10 },
    ],
    operators: [
      { key: "overbought", label: "Surachat", needsValue: true },
      { key: "oversold", label: "Survente", needsValue: true },
      { key: "cross_up", label: "%K croise au-dessus %D", needsValue: false },
      { key: "cross_down", label: "%K croise en-dessous %D", needsValue: false },
    ],
  },
  {
    key: "tsi",
    name: "TSI",
    category: "momentum",
    params: [
      { key: "long_period", label: "Long Period", type: "number", default: 25, min: 5, max: 100 },
      { key: "short_period", label: "Short Period", type: "number", default: 13, min: 2, max: 50 },
      { key: "signal_period", label: "Signal Period", type: "number", default: 7, min: 2, max: 30 },
    ],
    operators: [
      { key: "above_zero", label: "Au-dessus de zero", needsValue: false },
      { key: "below_zero", label: "En-dessous de zero", needsValue: false },
      { key: "above", label: "Au-dessus de", needsValue: true },
      { key: "below", label: "En-dessous de", needsValue: true },
      { key: "cross_up", label: "Croise au-dessus signal", needsValue: false },
      { key: "cross_down", label: "Croise en-dessous signal", needsValue: false },
    ],
  },

  // =====================================================================
  // VOLATILITY (4)
  // =====================================================================
  {
    key: "bollinger",
    name: "Bollinger Bands",
    category: "volatility",
    params: [
      { key: "period", label: "Period", type: "number", default: 20, min: 5, max: 200 },
      { key: "std_dev", label: "Std Dev", type: "number", default: 2.0, min: 0.5, max: 5, step: 0.1 },
    ],
    operators: [
      { key: "touch_upper", label: "Touche bande haute", needsValue: false },
      { key: "touch_lower", label: "Touche bande basse", needsValue: false },
      { key: "inside", label: "A l'interieur", needsValue: false },
      { key: "squeeze", label: "Compression", needsValue: false },
      { key: "expansion", label: "Expansion", needsValue: false },
      { key: "percent_b_above", label: "%B au-dessus de", needsValue: true },
      { key: "percent_b_below", label: "%B en-dessous de", needsValue: true },
    ],
  },
  {
    key: "adx_dmi",
    name: "ADX / DMI",
    category: "volatility",
    params: [
      { key: "period", label: "Period", type: "number", default: 14, min: 5, max: 50 },
    ],
    operators: [
      { key: "above", label: "ADX au-dessus de", needsValue: true },
      { key: "below", label: "ADX en-dessous de", needsValue: true },
      { key: "trending", label: "Tendance forte (>25)", needsValue: false },
      { key: "not_trending", label: "Pas de tendance (<20)", needsValue: false },
      { key: "bullish", label: "+DI > -DI", needsValue: false },
      { key: "bearish", label: "-DI > +DI", needsValue: false },
      { key: "di_cross_up", label: "+DI croise au-dessus -DI", needsValue: false },
      { key: "di_cross_down", label: "-DI croise au-dessus +DI", needsValue: false },
    ],
  },
  {
    key: "atr",
    name: "ATR",
    category: "volatility",
    params: [
      { key: "period", label: "Period", type: "number", default: 14, min: 2, max: 100 },
    ],
    operators: [
      { key: "above", label: "Au-dessus de", needsValue: true },
      { key: "below", label: "En-dessous de", needsValue: true },
      { key: "rising", label: "En hausse", needsValue: false },
      { key: "falling", label: "En baisse", needsValue: false },
    ],
  },
  {
    key: "keltner",
    name: "Keltner Channel",
    category: "volatility",
    params: [
      { key: "ema_period", label: "EMA Period", type: "number", default: 20, min: 5, max: 200 },
      { key: "atr_period", label: "ATR Period", type: "number", default: 10, min: 2, max: 50 },
      { key: "multiplier", label: "Multiplier", type: "number", default: 1.5, min: 0.5, max: 5, step: 0.1 },
    ],
    operators: [
      { key: "touch_upper", label: "Touche canal haut", needsValue: false },
      { key: "touch_lower", label: "Touche canal bas", needsValue: false },
      { key: "inside", label: "A l'interieur", needsValue: false },
      { key: "breakout_up", label: "Cassure haut", needsValue: false },
      { key: "breakout_down", label: "Cassure bas", needsValue: false },
    ],
  },

  // =====================================================================
  // VOLUME (3)
  // =====================================================================
  {
    key: "volume",
    name: "Volume",
    category: "volume",
    params: [
      { key: "sma_period", label: "SMA Period", type: "number", default: 20, min: 5, max: 200 },
      { key: "multiplier", label: "Multiplier", type: "number", default: 2.0, min: 1, max: 10, step: 0.1 },
    ],
    operators: [
      { key: "above_sma", label: "Au-dessus de la moyenne", needsValue: false },
      { key: "below_average", label: "En-dessous de la moyenne", needsValue: false },
      { key: "spike", label: "Pic de volume", needsValue: false },
      { key: "above_sma_multiplied", label: "Au-dessus x moyenne", needsValue: false },
      { key: "obv_rising", label: "OBV en hausse", needsValue: false },
      { key: "obv_falling", label: "OBV en baisse", needsValue: false },
    ],
  },
  {
    key: "chaikin_money_flow",
    name: "Chaikin Money Flow",
    category: "volume",
    params: [
      { key: "period", label: "Period", type: "number", default: 20, min: 5, max: 100 },
    ],
    operators: [
      { key: "positive", label: "Positif (pression acheteuse)", needsValue: false },
      { key: "negative", label: "Negatif (pression vendeuse)", needsValue: false },
      { key: "above", label: "Au-dessus de", needsValue: true },
      { key: "below", label: "En-dessous de", needsValue: true },
      { key: "rising", label: "En hausse", needsValue: false },
      { key: "falling", label: "En baisse", needsValue: false },
    ],
  },
  {
    key: "vwap",
    name: "VWAP",
    category: "volume",
    params: [
      { key: "band_multiplier", label: "Band Multiplier", type: "number", default: 2.0, min: 0.5, max: 5, step: 0.1 },
    ],
    operators: [
      { key: "price_above", label: "Prix au-dessus", needsValue: false },
      { key: "price_below", label: "Prix en-dessous", needsValue: false },
      { key: "cross_up", label: "Prix croise au-dessus", needsValue: false },
      { key: "cross_down", label: "Prix croise en-dessous", needsValue: false },
    ],
  },

  // =====================================================================
  // SPECIAL (3)
  // =====================================================================
  {
    key: "msb_glissant",
    name: "MSB Glissant",
    category: "special",
    params: [
      { key: "swing_lookback", label: "Swing Lookback", type: "number", default: 5, min: 2, max: 20 },
      { key: "bb_period", label: "BB Period", type: "number", default: 20, min: 5, max: 100 },
      { key: "bb_std_dev", label: "BB Std Dev", type: "number", default: 2.0, min: 0.5, max: 5, step: 0.1 },
    ],
    operators: [
      { key: "break_above", label: "Cassure haussiere", needsValue: false },
      { key: "break_below", label: "Cassure baissiere", needsValue: false },
      { key: "above_msb", label: "Au-dessus du MSB", needsValue: false },
      { key: "below_msb", label: "En-dessous du MSB", needsValue: false },
      { key: "break_detected", label: "Cassure detectee", needsValue: false },
    ],
  },
  {
    key: "fair_value_gap",
    name: "Fair Value Gap",
    category: "special",
    params: [
      { key: "lookback", label: "Lookback", type: "number", default: 50, min: 10, max: 200 },
      { key: "min_gap_pct", label: "Gap min (%)", type: "number", default: 0.05, min: 0.01, max: 1, step: 0.01 },
    ],
    operators: [
      { key: "in_bullish_fvg", label: "Dans FVG haussier", needsValue: false },
      { key: "in_bearish_fvg", label: "Dans FVG baissier", needsValue: false },
      { key: "near_bullish_fvg", label: "Proche FVG haussier", needsValue: false },
      { key: "near_bearish_fvg", label: "Proche FVG baissier", needsValue: false },
      { key: "fresh_bullish", label: "FVG haussier frais", needsValue: false },
      { key: "fresh_bearish", label: "FVG baissier frais", needsValue: false },
    ],
  },
  {
    key: "order_block",
    name: "Order Block",
    category: "special",
    params: [
      { key: "lookback", label: "Lookback", type: "number", default: 20, min: 5, max: 100 },
      { key: "min_impulse_pct", label: "Impulse min (%)", type: "number", default: 0.5, min: 0.1, max: 5, step: 0.1 },
    ],
    operators: [
      { key: "in_bullish_ob", label: "Dans OB haussier", needsValue: false },
      { key: "in_bearish_ob", label: "Dans OB baissier", needsValue: false },
      { key: "near_bullish_ob", label: "Proche OB haussier", needsValue: false },
      { key: "near_bearish_ob", label: "Proche OB baissier", needsValue: false },
      { key: "fresh_bullish", label: "OB haussier frais", needsValue: false },
      { key: "fresh_bearish", label: "OB baissier frais", needsValue: false },
    ],
  },
];

// Lookup helpers
export function getIndicator(key: string): IndicatorDef | undefined {
  return INDICATORS.find((i) => i.key === key);
}

export function getIndicatorsByCategory(): Record<IndicatorCategory, IndicatorDef[]> {
  const grouped: Record<IndicatorCategory, IndicatorDef[]> = {
    trend: [],
    momentum: [],
    volatility: [],
    volume: [],
    special: [],
  };
  for (const ind of INDICATORS) {
    grouped[ind.category].push(ind);
  }
  return grouped;
}

export function getDefaultParams(indicatorKey: string): Record<string, unknown> {
  const ind = getIndicator(indicatorKey);
  if (!ind) return {};
  const params: Record<string, unknown> = {};
  for (const p of ind.params) {
    params[p.key] = p.default;
  }
  return params;
}
