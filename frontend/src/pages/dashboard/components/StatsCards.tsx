import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatCurrency, formatPct } from "@/lib/utils";
import type { PortfolioOverview, TradeStats } from "@/types";
import {
  ArrowDownRight,
  ArrowUpRight,
  DollarSign,
  Percent,
  Target,
  TrendingUp,
} from "lucide-react";

interface StatsCardsProps {
  portfolio: PortfolioOverview | null;
  tradeStats: TradeStats | null;
  isLoading: boolean;
}

interface StatItem {
  title: string;
  value: string;
  change?: number;
  icon: React.ReactNode;
  iconBg: string;
}

const StatsCards = ({ portfolio, tradeStats, isLoading }: StatsCardsProps) => {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-5">
              <div className="flex items-center gap-4">
                <Skeleton className="w-12 h-12 rounded-xl" />
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-3 w-20" />
                  <Skeleton className="h-6 w-28" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const stats: StatItem[] = [
    {
      title: "Balance USDT",
      value: formatCurrency(portfolio?.total_value_usdt ?? 0),
      change: portfolio?.daily_pnl_pct,
      icon: <DollarSign className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />,
      iconBg: "bg-indigo-100 dark:bg-indigo-600/20",
    },
    {
      title: "Daily P&L",
      value: formatCurrency(portfolio?.daily_pnl_usdt ?? 0),
      change: portfolio?.daily_pnl_pct,
      icon: <TrendingUp className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />,
      iconBg: "bg-emerald-100 dark:bg-emerald-600/20",
    },
    {
      title: "Win Rate",
      value: formatPct(tradeStats?.win_rate ?? 0, 1).replace("+", ""),
      icon: <Target className="w-5 h-5 text-amber-600 dark:text-amber-400" />,
      iconBg: "bg-amber-100 dark:bg-amber-600/20",
    },
    {
      title: "Total P&L",
      value: formatCurrency(tradeStats?.total_pnl_usdt ?? 0),
      change: tradeStats?.total_pnl_pct,
      icon: <Percent className="w-5 h-5 text-cyan-600 dark:text-cyan-400" />,
      iconBg: "bg-cyan-100 dark:bg-cyan-600/20",
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <Card key={stat.title} className="hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-center gap-4">
              <div
                className={`w-12 h-12 rounded-xl flex items-center justify-center ${stat.iconBg}`}
              >
                {stat.icon}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                  {stat.title}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xl font-bold text-foreground truncate">
                    {stat.value}
                  </span>
                  {stat.change !== undefined && stat.change !== 0 && (
                    <span
                      className={`text-xs font-medium flex items-center gap-0.5 ${
                        stat.change >= 0
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-600 dark:text-red-400"
                      }`}
                    >
                      {stat.change >= 0 ? (
                        <ArrowUpRight className="w-3 h-3" />
                      ) : (
                        <ArrowDownRight className="w-3 h-3" />
                      )}
                      {formatPct(Math.abs(stat.change), 1)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default StatsCards;
