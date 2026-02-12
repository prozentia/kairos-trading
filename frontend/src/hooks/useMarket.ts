import { getAllPrices, getCandles, getTicker } from "@/api/market";
import type { Candle, Ticker } from "@/types";
import { useCallback, useEffect, useState } from "react";

export function useTicker(pair: string) {
  const [ticker, setTicker] = useState<Ticker | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchTicker = useCallback(async () => {
    try {
      const data = await getTicker(pair);
      setTicker(data);
    } catch (err) {
      console.error("Failed to fetch ticker:", err);
    } finally {
      setIsLoading(false);
    }
  }, [pair]);

  useEffect(() => {
    fetchTicker();
    // Refresh every 10 seconds
    const interval = setInterval(fetchTicker, 10000);
    return () => clearInterval(interval);
  }, [fetchTicker]);

  return { ticker, isLoading, refetch: fetchTicker };
}

export function useCandles(pair: string, timeframe = "5m", limit = 200) {
  const [candles, setCandles] = useState<Candle[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchCandles = useCallback(async () => {
    try {
      const data = await getCandles(pair, timeframe, limit);
      setCandles(data);
    } catch (err) {
      console.error("Failed to fetch candles:", err);
    } finally {
      setIsLoading(false);
    }
  }, [pair, timeframe, limit]);

  useEffect(() => {
    fetchCandles();
  }, [fetchCandles]);

  return { candles, isLoading, refetch: fetchCandles };
}

export function usePrices() {
  const [prices, setPrices] = useState<Array<{ pair: string; price: number; change_24h_pct: number }>>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchPrices = useCallback(async () => {
    try {
      const data = await getAllPrices();
      setPrices(data);
    } catch (err) {
      console.error("Failed to fetch prices:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPrices();
    const interval = setInterval(fetchPrices, 15000);
    return () => clearInterval(interval);
  }, [fetchPrices]);

  return { prices, isLoading, refetch: fetchPrices };
}
