import { addTradeJournal, getTrade, getTradeJournal } from "@/api/trades";
import SignalBadge from "@/components/shared/SignalBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn, formatCurrency, formatDate, formatDuration, formatPct } from "@/lib/utils";
import type { Trade, TradeJournal } from "@/types";
import {
  ArrowLeft,
  BookOpen,
  Calendar,
  Clock,
  DollarSign,
  Loader2,
  Send,
  Tag,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "react-toastify";

const TradeDetail = () => {
  const { tradeId } = useParams<{ tradeId: string }>();
  const [trade, setTrade] = useState<Trade | null>(null);
  const [journal, setJournal] = useState<TradeJournal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Journal form
  const [notes, setNotes] = useState("");
  const [tags, setTags] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const fetchTrade = useCallback(async () => {
    if (!tradeId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [tradeData, journalData] = await Promise.all([
        getTrade(tradeId),
        getTradeJournal(tradeId),
      ]);
      setTrade(tradeData);
      setJournal(journalData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch trade");
    } finally {
      setIsLoading(false);
    }
  }, [tradeId]);

  useEffect(() => {
    fetchTrade();
  }, [fetchTrade]);

  const handleAddJournal = async () => {
    if (!tradeId || !notes.trim()) return;
    setIsSaving(true);
    try {
      const entry = await addTradeJournal(tradeId, {
        notes: notes.trim(),
        tags: tags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      });
      setJournal((prev) => [...prev, entry]);
      setNotes("");
      setTags("");
      toast.success("Journal entry added");
    } catch {
      toast.error("Failed to add journal entry");
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Skeleton className="h-64 lg:col-span-2" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (error || !trade) {
    return (
      <div className="text-center py-16">
        <p className="text-destructive text-lg mb-4">
          {error ?? "Trade not found"}
        </p>
        <Link to="/trades">
          <Button variant="outline">
            <ArrowLeft className="w-4 h-4" />
            Back to Trades
          </Button>
        </Link>
      </div>
    );
  }

  const duration =
    trade.exit_time
      ? (new Date(trade.exit_time).getTime() -
          new Date(trade.entry_time).getTime()) /
        1000
      : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-4">
        <Link to="/trades">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4" />
            Back
          </Button>
        </Link>
        <h1 className="text-2xl font-bold text-foreground">
          {trade.pair.replace("USDT", "/USDT")}
        </h1>
        <SignalBadge side={trade.side} />
        <Badge
          variant={
            trade.status === "OPEN"
              ? "info"
              : trade.status === "CLOSED"
              ? "secondary"
              : "warning"
          }
        >
          {trade.status}
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Trade details */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Trade Details</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
              {/* Entry */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <DollarSign className="w-3 h-3" /> Entry Price
                </p>
                <p className="text-lg font-bold">
                  {formatCurrency(trade.entry_price)}
                </p>
              </div>

              {/* Exit */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <DollarSign className="w-3 h-3" /> Exit Price
                </p>
                <p className="text-lg font-bold">
                  {trade.exit_price
                    ? formatCurrency(trade.exit_price)
                    : "-"}
                </p>
              </div>

              {/* Quantity */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Quantity</p>
                <p className="text-lg font-bold">{trade.quantity.toFixed(6)}</p>
              </div>

              {/* P&L */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">P&L (USDT)</p>
                <p
                  className={cn(
                    "text-lg font-bold",
                    trade.pnl_usdt >= 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  )}
                >
                  {formatCurrency(trade.pnl_usdt)}
                </p>
              </div>

              {/* P&L % */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">P&L (%)</p>
                <p
                  className={cn(
                    "text-lg font-bold",
                    trade.pnl_pct >= 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  )}
                >
                  {formatPct(trade.pnl_pct)}
                </p>
              </div>

              {/* Fees */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Fees</p>
                <p className="text-lg font-bold text-muted-foreground">
                  {formatCurrency(trade.fees)}
                </p>
              </div>

              {/* Entry time */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Calendar className="w-3 h-3" /> Entry Time
                </p>
                <p className="text-sm font-medium">
                  {formatDate(trade.entry_time)}
                </p>
              </div>

              {/* Exit time */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Calendar className="w-3 h-3" /> Exit Time
                </p>
                <p className="text-sm font-medium">
                  {trade.exit_time ? formatDate(trade.exit_time) : "-"}
                </p>
              </div>

              {/* Duration */}
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Duration
                </p>
                <p className="text-sm font-medium">
                  {duration ? formatDuration(duration) : "Active"}
                </p>
              </div>
            </div>

            {/* Strategy & reasons */}
            <div className="mt-6 pt-6 border-t border-border space-y-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Strategy</p>
                <Badge variant="outline">{trade.strategy_name}</Badge>
              </div>
              {trade.entry_reason && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">
                    Entry Reason
                  </p>
                  <p className="text-sm text-foreground bg-muted/50 rounded-lg p-3">
                    {trade.entry_reason}
                  </p>
                </div>
              )}
              {trade.exit_reason && (
                <div>
                  <p className="text-xs text-muted-foreground mb-1">
                    Exit Reason
                  </p>
                  <p className="text-sm text-foreground bg-muted/50 rounded-lg p-3">
                    {trade.exit_reason}
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Journal sidebar */}
        <div className="space-y-6">
          {/* Add journal entry */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-primary" />
                Trade Journal
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                placeholder="Write your notes about this trade..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
              />
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Tags (comma separated)"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  className="flex-1 text-sm bg-transparent border-b border-border pb-1 outline-none text-foreground placeholder:text-muted-foreground"
                />
              </div>
              <Button
                onClick={handleAddJournal}
                disabled={!notes.trim() || isSaving}
                className="w-full"
                size="sm"
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
                Add Entry
              </Button>
            </CardContent>
          </Card>

          {/* Journal entries */}
          {journal.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-muted-foreground">
                  Journal Entries ({journal.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {journal.map((entry) => (
                  <div
                    key={entry.id}
                    className="border-l-2 border-primary/30 pl-3 space-y-1"
                  >
                    <p className="text-sm text-foreground">{entry.notes}</p>
                    {entry.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {entry.tags.map((tag) => (
                          <Badge
                            key={tag}
                            variant="outline"
                            className="text-[10px] px-1.5 py-0"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                    <p className="text-[10px] text-muted-foreground">
                      {formatDate(entry.created_at)}
                    </p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default TradeDetail;
