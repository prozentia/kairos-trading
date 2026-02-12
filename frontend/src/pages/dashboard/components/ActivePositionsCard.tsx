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
import type { Position } from "@/types";
import { Activity } from "lucide-react";

interface ActivePositionsCardProps {
  positions: Position[];
  isLoading: boolean;
}

const ActivePositionsCard = ({
  positions,
  isLoading,
}: ActivePositionsCardProps) => {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            Active Positions
          </CardTitle>
          <Badge variant="info" className="text-xs">
            {positions.length} open
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="px-0 pb-2">
        {isLoading ? (
          <div className="px-6 space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : positions.length === 0 ? (
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
                  <TableHead>Entry</TableHead>
                  <TableHead>Current</TableHead>
                  <TableHead>P&L</TableHead>
                  <TableHead className="pr-6">Strategy</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.map((pos) => (
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
                    <TableCell className="text-sm">
                      {formatCurrency(pos.entry_price)}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatCurrency(pos.current_price)}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span
                          className={cn(
                            "font-semibold text-sm",
                            pos.pnl_usdt >= 0
                              ? "text-green-600 dark:text-green-400"
                              : "text-red-600 dark:text-red-400"
                          )}
                        >
                          {formatCurrency(pos.pnl_usdt)}
                        </span>
                        <span
                          className={cn(
                            "text-xs",
                            pos.pnl_pct >= 0
                              ? "text-green-500/70"
                              : "text-red-500/70"
                          )}
                        >
                          {formatPct(pos.pnl_pct)}
                        </span>
                      </div>
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
  );
};

export default ActivePositionsCard;
