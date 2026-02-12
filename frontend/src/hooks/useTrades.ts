import { getTrades, getTradeStats } from "@/api/trades";
import type { TradeListResponse, TradeStats } from "@/types";
import { useCallback, useEffect, useState } from "react";

interface UseTradesOptions {
  pair?: string;
  strategy?: string;
  status?: string;
  page?: number;
  per_page?: number;
}

export function useTrades(options: UseTradesOptions = {}) {
  const [data, setData] = useState<TradeListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrades = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getTrades(options);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch trades");
    } finally {
      setIsLoading(false);
    }
  }, [options.pair, options.strategy, options.status, options.page, options.per_page]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  return { data, isLoading, error, refetch: fetchTrades };
}

export function useTradeStats(filters: Partial<UseTradesOptions> = {}) {
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await getTradeStats(filters);
      setStats(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch stats");
    } finally {
      setIsLoading(false);
    }
  }, [filters.pair, filters.strategy]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  return { stats, isLoading, error, refetch: fetchStats };
}
