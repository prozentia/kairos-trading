/**
 * Heikin-Ashi candle transformation (client-side).
 *
 * Converts standard OHLCV candles to Heikin-Ashi candles for
 * smoother trend visualisation.
 */

import type { Candle } from "@/types";

/**
 * Transform standard candles into Heikin-Ashi candles.
 *
 * Formulas:
 *   HA_Close = (Open + High + Low + Close) / 4
 *   HA_Open  = (prev_HA_Open + prev_HA_Close) / 2
 *   HA_High  = max(High, HA_Open, HA_Close)
 *   HA_Low   = min(Low, HA_Open, HA_Close)
 */
export function toHeikinAshi(candles: Candle[]): Candle[] {
  if (candles.length === 0) return [];

  const result: Candle[] = [];

  // First candle
  const first = candles[0];
  let haClose = (first.open + first.high + first.low + first.close) / 4;
  let haOpen = (first.open + first.close) / 2;
  let haHigh = Math.max(first.high, haOpen, haClose);
  let haLow = Math.min(first.low, haOpen, haClose);

  result.push({
    timestamp: first.timestamp,
    open: haOpen,
    high: haHigh,
    low: haLow,
    close: haClose,
    volume: first.volume,
  });

  // Remaining candles
  for (let i = 1; i < candles.length; i++) {
    const c = candles[i];
    const prevHa = result[i - 1];

    haClose = (c.open + c.high + c.low + c.close) / 4;
    haOpen = (prevHa.open + prevHa.close) / 2;
    haHigh = Math.max(c.high, haOpen, haClose);
    haLow = Math.min(c.low, haOpen, haClose);

    result.push({
      timestamp: c.timestamp,
      open: haOpen,
      high: haHigh,
      low: haLow,
      close: haClose,
      volume: c.volume,
    });
  }

  return result;
}
