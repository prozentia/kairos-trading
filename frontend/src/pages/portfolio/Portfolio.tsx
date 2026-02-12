import { getAllocation, getEquityCurve, getPortfolio, getRiskMetrics } from "@/api/portfolio";
import PnlChart from "@/components/charts/PnlChart";
import PortfolioDonut from "@/components/charts/PortfolioDonut";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn, formatCurrency, formatPct } from "@/lib/utils";
import type { PortfolioOverview } from "@/types";
import {
  BarChart3,
  DollarSign,
  PieChart,
  Shield,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

const Portfolio = () => {
  const [portfolio, setPortfolio] = useState<PortfolioOverview | null>(null);
  const [allocation, setAllocation] = useState<
    Array<{ pair: string; value_usdt: number; pct: number }>
  >([]);
  const [equityCurve, setEquityCurve] = useState<
    Array<{ date: string; pnl: number }>
  >([]);
  const [riskMetrics, setRiskMetrics] = useState<Record<string, number> | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [portfolioData, allocationData, equityData, riskData] =
        await Promise.allSettled([
          getPortfolio(),
          getAllocation(),
          getEquityCurve(30),
          getRiskMetrics(),
        ]);

      if (portfolioData.status === "fulfilled") {
        setPortfolio(portfolioData.value);
      }
      if (allocationData.status === "fulfilled") {
        setAllocation(allocationData.value);
      }
      if (equityData.status === "fulfilled") {
        setEquityCurve(equityData.value);
      }
      if (riskData.status === "fulfilled") {
        setRiskMetrics(riskData.value);
      }
    } catch (err) {
      console.error("Failed to fetch portfolio data:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-4 w-16 mb-2" />
                <Skeleton className="h-7 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-[350px]" />
          <Skeleton className="h-[350px]" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <Wallet className="w-4 h-4 text-indigo-500" />
              <span className="text-xs text-muted-foreground">Total Value</span>
            </div>
            <p className="text-xl font-bold">
              {formatCurrency(portfolio?.total_value_usdt ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <DollarSign className="w-4 h-4 text-green-500" />
              <span className="text-xs text-muted-foreground">Available</span>
            </div>
            <p className="text-xl font-bold">
              {formatCurrency(portfolio?.available_usdt ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <TrendingUp className="w-4 h-4 text-amber-500" />
              <span className="text-xs text-muted-foreground">Daily P&L</span>
            </div>
            <p
              className={cn(
                "text-xl font-bold",
                (portfolio?.daily_pnl_usdt ?? 0) >= 0
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-600 dark:text-red-400"
              )}
            >
              {formatCurrency(portfolio?.daily_pnl_usdt ?? 0)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="w-4 h-4 text-cyan-500" />
              <span className="text-xs text-muted-foreground">Exposure</span>
            </div>
            <p className="text-xl font-bold">
              {(portfolio?.exposure_pct ?? 0).toFixed(1)}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Equity curve */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-primary" />
              Equity Curve (30 days)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <PnlChart data={equityCurve} chartHeight={280} />
          </CardContent>
        </Card>

        {/* Allocation donut */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <PieChart className="w-4 h-4 text-primary" />
              Asset Allocation
            </CardTitle>
          </CardHeader>
          <CardContent>
            <PortfolioDonut
              data={allocation.map((a) => ({
                label: a.pair,
                value: a.pct,
              }))}
              chartHeight={280}
            />
          </CardContent>
        </Card>
      </div>

      {/* Open positions table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Open Positions</CardTitle>
            <Badge variant="info" className="text-xs">
              {portfolio?.positions?.length ?? 0} open
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="px-0 pb-2">
          {!portfolio?.positions?.length ? (
            <div className="px-6 py-8 text-center text-muted-foreground text-sm">
              No open positions.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-6">Pair</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead>Entry Price</TableHead>
                    <TableHead>Current Price</TableHead>
                    <TableHead>Quantity</TableHead>
                    <TableHead>P&L</TableHead>
                    <TableHead>Stop Loss</TableHead>
                    <TableHead className="pr-6">Strategy</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {portfolio.positions.map((pos) => (
                    <TableRow key={`${pos.pair}-${pos.entry_time}`}>
                      <TableCell className="pl-6 font-medium">
                        {pos.pair.replace("USDT", "/USDT")}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={pos.side === "LONG" ? "success" : "danger"}
                          className="text-xs"
                        >
                          {pos.side}
                        </Badge>
                      </TableCell>
                      <TableCell>{formatCurrency(pos.entry_price)}</TableCell>
                      <TableCell>{formatCurrency(pos.current_price)}</TableCell>
                      <TableCell>{pos.quantity.toFixed(6)}</TableCell>
                      <TableCell>
                        <div>
                          <span
                            className={cn(
                              "font-semibold",
                              pos.pnl_usdt >= 0
                                ? "text-green-600 dark:text-green-400"
                                : "text-red-600 dark:text-red-400"
                            )}
                          >
                            {formatCurrency(pos.pnl_usdt)}
                          </span>
                          <span
                            className={cn(
                              "text-xs ml-1",
                              pos.pnl_pct >= 0
                                ? "text-green-500/70"
                                : "text-red-500/70"
                            )}
                          >
                            ({formatPct(pos.pnl_pct)})
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {pos.stop_loss ? formatCurrency(pos.stop_loss) : "-"}
                      </TableCell>
                      <TableCell className="pr-6 text-xs text-muted-foreground">
                        {pos.strategy_name}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Risk metrics */}
      {riskMetrics && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" />
              Risk Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {Object.entries(riskMetrics).map(([key, value]) => (
                <div key={key} className="bg-muted/50 rounded-lg p-3">
                  <p className="text-xs text-muted-foreground capitalize">
                    {key.replace(/_/g, " ")}
                  </p>
                  <p className="text-lg font-bold mt-0.5">
                    {typeof value === "number" ? value.toFixed(2) : value}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Portfolio;
