import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useDailyStats, usePerformanceKPIs } from "@/hooks/usePerformance";
import {
  Activity,
  BarChart3,
  TrendingDown,
  TrendingUp,
  Trophy,
  Target,
} from "lucide-react";

const Performance = () => {
  const { kpis, isLoading: kpisLoading } = usePerformanceKPIs();
  const { stats, isLoading: statsLoading } = useDailyStats();

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 className="h-8 w-8 text-primary" />
        <div>
          <h1 className="text-2xl font-bold">Performance</h1>
          <p className="text-muted-foreground">
            Métriques de trading et analyse de performance
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Win Rate"
          value={kpis?.win_rate}
          suffix="%"
          icon={<Trophy className="h-4 w-4" />}
          loading={kpisLoading}
          color={kpis?.win_rate && kpis.win_rate >= 50 ? "text-green-500" : "text-red-500"}
        />
        <KPICard
          title="R Moyen"
          value={kpis?.avg_rr}
          suffix="R"
          icon={<Target className="h-4 w-4" />}
          loading={kpisLoading}
          color={kpis?.avg_rr && kpis.avg_rr >= 1.5 ? "text-green-500" : "text-yellow-500"}
        />
        <KPICard
          title="PnL Total"
          value={kpis?.total_pnl}
          suffix=" USDT"
          icon={kpis?.total_pnl && kpis.total_pnl >= 0
            ? <TrendingUp className="h-4 w-4" />
            : <TrendingDown className="h-4 w-4" />}
          loading={kpisLoading}
          color={kpis?.total_pnl && kpis.total_pnl >= 0 ? "text-green-500" : "text-red-500"}
        />
        <KPICard
          title="Max Drawdown"
          value={kpis?.max_drawdown}
          suffix="%"
          icon={<Activity className="h-4 w-4" />}
          loading={kpisLoading}
          color="text-orange-500"
        />
      </div>

      {/* Daily Stats Table */}
      <Card>
        <CardHeader>
          <CardTitle>Statistiques Journalières</CardTitle>
        </CardHeader>
        <CardContent>
          {statsLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : stats && stats.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">Date</th>
                    <th className="pb-2 pr-4">Trades</th>
                    <th className="pb-2 pr-4">Win Rate</th>
                    <th className="pb-2 pr-4">PnL</th>
                    <th className="pb-2 pr-4">R Moyen</th>
                    <th className="pb-2">Drawdown</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.map((day: any) => (
                    <tr key={day.date} className="border-b">
                      <td className="py-2 pr-4 font-medium">{day.date}</td>
                      <td className="py-2 pr-4">{day.trades_count}</td>
                      <td className="py-2 pr-4">{day.win_rate?.toFixed(1)}%</td>
                      <td className={`py-2 pr-4 font-medium ${
                        day.pnl >= 0 ? "text-green-500" : "text-red-500"
                      }`}>
                        {day.pnl >= 0 ? "+" : ""}{day.pnl?.toFixed(2)} USDT
                      </td>
                      <td className="py-2 pr-4">{day.avg_rr?.toFixed(2)}R</td>
                      <td className="py-2 text-orange-500">
                        {day.max_drawdown?.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-center text-muted-foreground py-8">
              Aucune donnée de performance disponible
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

interface KPICardProps {
  title: string;
  value: number | undefined;
  suffix: string;
  icon: React.ReactNode;
  loading: boolean;
  color: string;
}

const KPICard = ({ title, value, suffix, icon, loading, color }: KPICardProps) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">
        {title}
      </CardTitle>
      {icon}
    </CardHeader>
    <CardContent>
      {loading ? (
        <Skeleton className="h-8 w-20" />
      ) : (
        <div className={`text-2xl font-bold ${color}`}>
          {value !== undefined ? `${value.toFixed(2)}${suffix}` : "—"}
        </div>
      )}
    </CardContent>
  </Card>
);

export default Performance;
