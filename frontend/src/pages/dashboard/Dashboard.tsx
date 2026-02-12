import { getPortfolio } from "@/api/portfolio";
import { useTrades, useTradeStats } from "@/hooks/useTrades";
import type { PortfolioOverview } from "@/types";
import { useCallback, useEffect, useState } from "react";
import ActivePositionsCard from "./components/ActivePositionsCard";
import BotControlCard from "./components/BotControlCard";
import LiveChartCard from "./components/LiveChartCard";
import RecentTradesCard from "./components/RecentTradesCard";
import StatsCards from "./components/StatsCards";
import TrustScoreCard from "./components/TrustScoreCard";

const Dashboard = () => {
  // Portfolio data (balance, positions, P&L)
  const [portfolio, setPortfolio] = useState<PortfolioOverview | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState(true);

  // Trades data
  const { data: tradesData, isLoading: tradesLoading } = useTrades({
    per_page: 8,
    page: 1,
  });
  const { stats: tradeStats, isLoading: statsLoading } = useTradeStats();

  // Fetch portfolio
  const fetchPortfolio = useCallback(async () => {
    try {
      const data = await getPortfolio();
      setPortfolio(data);
    } catch (err) {
      console.error("Failed to fetch portfolio:", err);
    } finally {
      setPortfolioLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolio();
    // Refresh portfolio every 30 seconds
    const interval = setInterval(fetchPortfolio, 30000);
    return () => clearInterval(interval);
  }, [fetchPortfolio]);

  // Trust score: in a real app this would come from the backend
  // For now use a calculated value based on trade stats
  const trustScore = tradeStats
    ? Math.min(
        100,
        Math.max(
          0,
          Math.round(
            tradeStats.win_rate * 0.4 +
              (tradeStats.profit_factor > 0
                ? Math.min(tradeStats.profit_factor * 10, 30)
                : 0) +
              Math.min(tradeStats.total_trades * 0.5, 30)
          )
        )
      )
    : 46;

  return (
    <div className="space-y-6">
      {/* Stats cards row */}
      <StatsCards
        portfolio={portfolio}
        tradeStats={tradeStats}
        isLoading={portfolioLoading || statsLoading}
      />

      {/* Main content grid: chart + sidebar */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Live chart - takes 2 columns */}
        <LiveChartCard pair="BTCUSDT" />

        {/* Sidebar: bot control + trust score */}
        <div className="space-y-6">
          <BotControlCard />
          <TrustScoreCard score={trustScore} isLoading={statsLoading} />
        </div>
      </div>

      {/* Bottom row: positions + recent trades */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <ActivePositionsCard
          positions={portfolio?.positions ?? []}
          isLoading={portfolioLoading}
        />
        <RecentTradesCard
          trades={tradesData?.trades ?? []}
          isLoading={tradesLoading}
        />
      </div>
    </div>
  );
};

export default Dashboard;
