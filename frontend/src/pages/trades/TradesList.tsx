import { exportTradesCsv } from "@/api/trades";
import SignalBadge from "@/components/shared/SignalBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useTrades, useTradeStats } from "@/hooks/useTrades";
import { cn, formatCurrency, formatDate, formatDuration, formatPct } from "@/lib/utils";
import {
  ArrowDownRight,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
  Download,
  Filter,
  Search,
  Target,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-toastify";

const TradesList = () => {
  // Filters state
  const [page, setPage] = useState(1);
  const [pair, setPair] = useState<string>("");
  const [status, setStatus] = useState<string>("");
  const [strategy, setStrategy] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  const perPage = 15;

  const { data, isLoading, error } = useTrades({
    page,
    per_page: perPage,
    pair: pair || undefined,
    status: status || undefined,
    strategy: strategy || undefined,
  });

  const { stats, isLoading: statsLoading } = useTradeStats({
    pair: pair || undefined,
    strategy: strategy || undefined,
  });

  // CSV export handler
  const handleExport = async () => {
    try {
      const blob = await exportTradesCsv({
        pair: pair || undefined,
        status: status || undefined,
        strategy: strategy || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `kairos-trades-${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Trades exported successfully");
    } catch {
      toast.error("Failed to export trades");
    }
  };

  const totalPages = data?.pages ?? 1;

  return (
    <div className="space-y-6">
      {/* Stats summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {statsLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <Skeleton className="h-4 w-16 mb-2" />
                <Skeleton className="h-7 w-24" />
              </CardContent>
            </Card>
          ))
        ) : (
          <>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground mb-1">Total Trades</p>
                <p className="text-xl font-bold">{stats?.total_trades ?? 0}</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                  <Target className="w-3 h-3" /> Win Rate
                </p>
                <p className="text-xl font-bold">
                  {(stats?.win_rate ?? 0).toFixed(1)}%
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                  <TrendingUp className="w-3 h-3" /> Total P&L
                </p>
                <p
                  className={cn(
                    "text-xl font-bold",
                    (stats?.total_pnl_usdt ?? 0) >= 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  )}
                >
                  {formatCurrency(stats?.total_pnl_usdt ?? 0)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <p className="text-xs text-muted-foreground mb-1">Profit Factor</p>
                <p className="text-xl font-bold">
                  {(stats?.profit_factor ?? 0).toFixed(2)}
                </p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {/* Trades table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle className="text-lg">Trade History</CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFilters(!showFilters)}
              >
                <Filter className="w-4 h-4" />
                Filters
              </Button>
              <Button variant="outline" size="sm" onClick={handleExport}>
                <Download className="w-4 h-4" />
                CSV
              </Button>
            </div>
          </div>

          {/* Filters panel */}
          {showFilters && (
            <div className="mt-4 flex flex-wrap items-center gap-3 pt-4 border-t border-border">
              <div className="relative flex-1 min-w-[180px]">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Filter by pair..."
                  value={pair}
                  onChange={(e) => {
                    setPair(e.target.value.toUpperCase());
                    setPage(1);
                  }}
                  className="pl-9 h-9"
                />
              </div>
              <Select
                value={status}
                onValueChange={(val) => {
                  setStatus(val === "ALL" ? "" : val);
                  setPage(1);
                }}
              >
                <SelectTrigger className="w-[140px] h-9">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Status</SelectItem>
                  <SelectItem value="OPEN">Open</SelectItem>
                  <SelectItem value="CLOSED">Closed</SelectItem>
                  <SelectItem value="CANCELLED">Cancelled</SelectItem>
                </SelectContent>
              </Select>
              <Input
                placeholder="Strategy..."
                value={strategy}
                onChange={(e) => {
                  setStrategy(e.target.value);
                  setPage(1);
                }}
                className="w-[160px] h-9"
              />
              {(pair || status || strategy) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setPair("");
                    setStatus("");
                    setStrategy("");
                    setPage(1);
                  }}
                >
                  Clear
                </Button>
              )}
            </div>
          )}
        </CardHeader>

        <CardContent className="px-0 pb-4">
          {isLoading ? (
            <div className="px-6 space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-11 w-full" />
              ))}
            </div>
          ) : error ? (
            <div className="px-6 py-8 text-center text-destructive">
              {error}
            </div>
          ) : !data?.trades?.length ? (
            <div className="px-6 py-12 text-center text-muted-foreground">
              No trades found matching your criteria.
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="pl-6">Pair</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead>Entry</TableHead>
                      <TableHead>Exit</TableHead>
                      <TableHead>Qty</TableHead>
                      <TableHead>P&L</TableHead>
                      <TableHead>P&L %</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Strategy</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="pr-6">Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.trades.map((trade) => (
                      <TableRow key={trade.id} className="hover:bg-muted/30">
                        <TableCell className="pl-6">
                          <Link
                            to={`/trades/${trade.id}`}
                            className="font-medium text-primary hover:underline"
                          >
                            {trade.pair.replace("USDT", "/USDT")}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <SignalBadge side={trade.side} />
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatCurrency(trade.entry_price)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {trade.exit_price
                            ? formatCurrency(trade.exit_price)
                            : "-"}
                        </TableCell>
                        <TableCell className="text-sm">
                          {trade.quantity.toFixed(6)}
                        </TableCell>
                        <TableCell>
                          <span
                            className={cn(
                              "font-semibold text-sm inline-flex items-center gap-0.5",
                              trade.pnl_usdt >= 0
                                ? "text-green-600 dark:text-green-400"
                                : "text-red-600 dark:text-red-400"
                            )}
                          >
                            {trade.pnl_usdt >= 0 ? (
                              <ArrowUpRight className="w-3 h-3" />
                            ) : (
                              <ArrowDownRight className="w-3 h-3" />
                            )}
                            {formatCurrency(Math.abs(trade.pnl_usdt))}
                          </span>
                        </TableCell>
                        <TableCell>
                          <span
                            className={cn(
                              "text-sm",
                              trade.pnl_pct >= 0
                                ? "text-green-600 dark:text-green-400"
                                : "text-red-600 dark:text-red-400"
                            )}
                          >
                            {formatPct(trade.pnl_pct)}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {trade.exit_time
                            ? formatDuration(
                                (new Date(trade.exit_time).getTime() -
                                  new Date(trade.entry_time).getTime()) /
                                  1000
                              )
                            : "Active"}
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground max-w-[120px] truncate">
                          {trade.strategy_name}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              trade.status === "OPEN"
                                ? "info"
                                : trade.status === "CLOSED"
                                ? "secondary"
                                : "warning"
                            }
                            className="text-xs"
                          >
                            {trade.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="pr-6 text-sm text-muted-foreground whitespace-nowrap">
                          {formatDate(trade.entry_time)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 pt-4 border-t border-border mt-2">
                  <p className="text-sm text-muted-foreground">
                    Page {data.page} of {totalPages} ({data.total} trades)
                  </p>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page <= 1}
                    >
                      <ChevronLeft className="w-4 h-4" />
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        setPage((p) => Math.min(totalPages, p + 1))
                      }
                      disabled={page >= totalPages}
                    >
                      Next
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default TradesList;
