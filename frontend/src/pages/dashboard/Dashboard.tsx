import { getPortfolio } from "@/api/portfolio";
import { useBotStatus } from "@/hooks/useBot";
import { useTrades, useTradeStats } from "@/hooks/useTrades";
import type { PortfolioOverview } from "@/types";
import { useCallback, useEffect, useState } from "react";
import ActivePositionsCard from "./components/ActivePositionsCard";
import BotControlCard from "./components/BotControlCard";
import LiveChartCard from "./components/LiveChartCard";
import RecentTradesCard from "./components/RecentTradesCard";
import StatsCards from "./components/StatsCards";
import TrustScoreCard from "./components/TrustScoreCard";

// Map trust level name to approximate score for the gauge
const TRUST_LEVEL_SCORES: Record<string, number> = {
  CRAWL: 20,
  WALK: 52,
  RUN: 72,
  SPRINT: 90,
};

const DEFAULT_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];

const Dashboard = () => {
  // Bot status (strategy, trust level)
  const { status: botStatus } = useBotStatus();

  // Selected pair for the chart
  const [selectedPair, setSelectedPair] = useState("BTCUSDT");

  // Available pairs from engine, fallback to defaults
  const pairs =
    botStatus?.pairs_active && botStatus.pairs_active.length > 0
      ? botStatus.pairs_active
      : DEFAULT_PAIRS;

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
    const interval = setInterval(fetchPortfolio, 30000);
    return () => clearInterval(interval);
  }, [fetchPortfolio]);

  // Trust score from backend trust_level
  const trustScore = TRUST_LEVEL_SCORES[botStatus?.trust_level ?? "CRAWL"] ?? 20;

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
        <LiveChartCard
          pair={selectedPair}
          pairs={pairs}
          onPairChange={setSelectedPair}
        />

        {/* Sidebar: bot control + trust score */}
        <div className="space-y-6">
          <BotControlCard />
          <TrustScoreCard score={trustScore} isLoading={false} />
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
