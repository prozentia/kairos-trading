import BotStatusBadge from "@/components/shared/BotStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useBotControls, useBotStatus } from "@/hooks/useBot";
import { formatDuration } from "@/lib/utils";
import {
  Bot,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Settings,
} from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "react-toastify";

const BotControlCard = () => {
  const { status, isLoading, refetch } = useBotStatus();
  const { start, stop, isStarting, isStopping } = useBotControls();

  const handleStart = async () => {
    try {
      await start();
      toast.success("Bot started successfully");
      refetch();
    } catch {
      toast.error("Failed to start bot");
    }
  };

  const handleStop = async () => {
    try {
      await stop();
      toast.info("Bot stopped");
      refetch();
    } catch {
      toast.error("Failed to stop bot");
    }
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bot className="w-4 h-4 text-primary" />
            Bot Control
          </CardTitle>
          <Link to="/bot">
            <Button variant="ghost" size="icon-sm">
              <Settings className="w-4 h-4" />
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Status badge */}
            <div className="flex items-center justify-between">
              <BotStatusBadge
                running={status?.running ?? false}
                mode={status?.mode}
              />
              {status?.running && (
                <span className="text-xs text-muted-foreground">
                  Uptime: {formatDuration(status.uptime_seconds)}
                </span>
              )}
            </div>

            {/* Active strategy */}
            {status?.strategy && (
              <div className="bg-primary/10 rounded-lg px-3 py-2">
                <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Strategy</p>
                <p className="text-sm font-bold text-primary">{status.strategy}</p>
              </div>
            )}

            {/* Quick stats */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Pairs</p>
                <p className="text-lg font-bold text-foreground">
                  {status?.pairs_active?.length ?? 0}
                </p>
              </div>
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Positions</p>
                <p className="text-lg font-bold text-foreground">
                  {status?.open_positions ?? 0}
                </p>
              </div>
            </div>

            {/* Mode + daily stats */}
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">Mode:</span>
                <span
                  className={`font-semibold ${
                    status?.mode === "live"
                      ? "text-green-600 dark:text-green-400"
                      : "text-amber-600 dark:text-amber-400"
                  }`}
                >
                  {status?.mode === "live" ? "LIVE" : "DRY RUN"}
                </span>
              </div>
              {(status?.daily_trades ?? 0) > 0 && (
                <span className="text-xs text-muted-foreground">
                  {status?.daily_trades} trades today
                </span>
              )}
            </div>

            {/* Control buttons */}
            <div className="flex gap-2">
              {status?.running ? (
                <Button
                  variant="destructive"
                  className="flex-1"
                  onClick={handleStop}
                  disabled={isStopping}
                >
                  {isStopping ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Pause className="w-4 h-4" />
                  )}
                  Stop
                </Button>
              ) : (
                <Button
                  variant="success"
                  className="flex-1"
                  onClick={handleStart}
                  disabled={isStarting}
                >
                  {isStarting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Start
                </Button>
              )}
              <Button
                variant="outline"
                size="icon"
                onClick={() => refetch()}
                title="Refresh status"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default BotControlCard;
