import SignalBadge from "@/components/shared/SignalBadge";
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
import { cn, formatCurrency, formatDate } from "@/lib/utils";
import type { Trade } from "@/types";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

interface RecentTradesCardProps {
  trades: Trade[];
  isLoading: boolean;
}

const RecentTradesCard = ({ trades, isLoading }: RecentTradesCardProps) => {
  // Show max 8 recent trades
  const recentTrades = trades.slice(0, 8);

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Recent Trades</CardTitle>
          <Link
            to="/trades"
            className="text-sm text-primary hover:underline inline-flex items-center gap-1"
          >
            View all <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-2">
        {isLoading ? (
          <div className="px-6 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : recentTrades.length === 0 ? (
          <div className="px-6 py-8 text-center text-muted-foreground text-sm">
            No trades recorded yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-6">Pair</TableHead>
                  <TableHead>Side</TableHead>
                  <TableHead>P&L</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="pr-6">Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentTrades.map((trade) => (
                  <TableRow key={trade.id} className="hover:bg-muted/30">
                    <TableCell className="pl-6 font-medium">
                      <Link
                        to={`/trades/${trade.id}`}
                        className="hover:text-primary transition-colors"
                      >
                        {trade.pair.replace("USDT", "/USDT")}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <SignalBadge side={trade.side} />
                    </TableCell>
                    <TableCell>
                      <span
                        className={cn(
                          "font-semibold text-sm",
                          trade.pnl_usdt >= 0
                            ? "text-green-600 dark:text-green-400"
                            : "text-red-600 dark:text-red-400"
                        )}
                      >
                        {formatCurrency(trade.pnl_usdt)}
                      </span>
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
                    <TableCell className="pr-6 text-sm text-muted-foreground">
                      {formatDate(trade.entry_time)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default RecentTradesCard;
