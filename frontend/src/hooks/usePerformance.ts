import { useQuery } from "@tanstack/react-query";
import apiClient from "@/api/client";

interface KPIs {
  win_rate: number;
  avg_rr: number;
  total_pnl: number;
  max_drawdown: number;
  total_trades: number;
  sharpe_ratio: number;
}

interface DailyStat {
  date: string;
  trades_count: number;
  win_rate: number;
  pnl: number;
  avg_rr: number;
  max_drawdown: number;
}

export const usePerformanceKPIs = () => {
  const { data, isLoading, error } = useQuery<KPIs>({
    queryKey: ["performance-kpis"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/performance/kpis");
      return res.data;
    },
    refetchInterval: 30000,
  });

  return { kpis: data, isLoading, error };
};

export const useDailyStats = () => {
  const { data, isLoading, error } = useQuery<DailyStat[]>({
    queryKey: ["daily-stats"],
    queryFn: async () => {
      const res = await apiClient.get("/api/v1/performance/daily");
      return res.data;
    },
    refetchInterval: 60000,
  });

  return { stats: data, isLoading, error };
};
