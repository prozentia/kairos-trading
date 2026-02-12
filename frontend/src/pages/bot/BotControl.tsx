import { restartBot, updateBotConfig } from "@/api/bot";
import BotStatusBadge from "@/components/shared/BotStatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { useBotConfig, useBotControls, useBotStatus } from "@/hooks/useBot";
import { formatDuration } from "@/lib/utils";
import type { BotConfig } from "@/types";
import {
  Activity,
  Bot,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  Save,
  ScrollText,
  Settings,
  Zap,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-toastify";

const BotControl = () => {
  const { status, isLoading: statusLoading, refetch: refetchStatus } = useBotStatus();
  const { config, isLoading: configLoading, refetch: refetchConfig } = useBotConfig();
  const { start, stop, isStarting, isStopping } = useBotControls();

  // Editable config state
  const [editConfig, setEditConfig] = useState<Partial<BotConfig>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);

  // Sync edit config when loaded
  useEffect(() => {
    if (config) {
      setEditConfig(config);
    }
  }, [config]);

  const updateField = <K extends keyof BotConfig>(
    field: K,
    value: BotConfig[K]
  ) => {
    setEditConfig((prev) => ({ ...prev, [field]: value }));
  };

  const handleStart = async () => {
    try {
      await start();
      toast.success("Bot started");
      refetchStatus();
    } catch {
      toast.error("Failed to start bot");
    }
  };

  const handleStop = async () => {
    try {
      await stop();
      toast.info("Bot stopped");
      refetchStatus();
    } catch {
      toast.error("Failed to stop bot");
    }
  };

  const handleRestart = async () => {
    setIsRestarting(true);
    try {
      await restartBot();
      toast.success("Bot restarting...");
      refetchStatus();
    } catch {
      toast.error("Failed to restart bot");
    } finally {
      setIsRestarting(false);
    }
  };

  const handleSaveConfig = async () => {
    setIsSaving(true);
    try {
      await updateBotConfig(editConfig);
      toast.success("Configuration saved");
      refetchConfig();
    } catch {
      toast.error("Failed to save configuration");
    } finally {
      setIsSaving(false);
    }
  };

  const isLoading = statusLoading || configLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Bot className="w-6 h-6 text-primary" />
            Bot Control
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your trading bot
          </p>
        </div>
        <Link to="/bot/logs">
          <Button variant="outline" size="sm">
            <ScrollText className="w-4 h-4" />
            View Logs
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Status & controls */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" />
              Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                <Skeleton className="h-8 w-32" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : (
              <div className="space-y-5">
                {/* Status badge */}
                <div className="flex items-center justify-between">
                  <BotStatusBadge
                    running={status?.running ?? false}
                    mode={status?.mode}
                  />
                  {status?.version && (
                    <Badge variant="outline" className="text-xs">
                      v{status.version}
                    </Badge>
                  )}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-xs text-muted-foreground">Uptime</p>
                    <p className="text-lg font-bold">
                      {status?.running
                        ? formatDuration(status.uptime_seconds)
                        : "--"}
                    </p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-xs text-muted-foreground">Positions</p>
                    <p className="text-lg font-bold">
                      {status?.open_positions ?? 0}
                    </p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-xs text-muted-foreground">Active Pairs</p>
                    <p className="text-lg font-bold">
                      {status?.pairs_active?.length ?? 0}
                    </p>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-3">
                    <p className="text-xs text-muted-foreground">Mode</p>
                    <p
                      className={`text-lg font-bold ${
                        status?.mode === "live"
                          ? "text-green-600 dark:text-green-400"
                          : "text-amber-600 dark:text-amber-400"
                      }`}
                    >
                      {status?.mode === "live" ? "LIVE" : "DRY"}
                    </p>
                  </div>
                </div>

                {/* Active pairs list */}
                {status?.pairs_active && status.pairs_active.length > 0 && (
                  <div>
                    <p className="text-xs text-muted-foreground mb-1.5">
                      Active Pairs
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {status.pairs_active.map((pair) => (
                        <Badge
                          key={pair}
                          variant="outline"
                          className="text-xs"
                        >
                          {pair}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Last signal */}
                {status?.last_signal_time && (
                  <p className="text-xs text-muted-foreground">
                    Last signal:{" "}
                    {new Date(status.last_signal_time).toLocaleString()}
                  </p>
                )}

                <Separator />

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
                    onClick={handleRestart}
                    disabled={isRestarting || !status?.running}
                  >
                    {isRestarting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                    Restart
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Configuration */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg flex items-center gap-2">
                <Settings className="w-4 h-4 text-primary" />
                Configuration
              </CardTitle>
              <Button
                size="sm"
                onClick={handleSaveConfig}
                disabled={isSaving}
              >
                {isSaving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Save
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : (
              <div className="space-y-6">
                {/* Mode section */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Zap className="w-3.5 h-3.5" />
                    Trading Mode
                  </h3>
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Dry Run Mode</Label>
                      <p className="text-xs text-muted-foreground">
                        Simulate trades without real money
                      </p>
                    </div>
                    <Switch
                      checked={editConfig.dry_run ?? true}
                      onCheckedChange={(val) => updateField("dry_run", val)}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Telegram Notifications</Label>
                      <p className="text-xs text-muted-foreground">
                        Send trade alerts via Telegram
                      </p>
                    </div>
                    <Switch
                      checked={editConfig.telegram_enabled ?? false}
                      onCheckedChange={(val) =>
                        updateField("telegram_enabled", val)
                      }
                    />
                  </div>
                </div>

                <Separator />

                {/* Strategy section */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground">
                    Strategy
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Strategy Type</Label>
                      <Input
                        value={editConfig.strategy_type ?? ""}
                        onChange={(e) =>
                          updateField("strategy_type", e.target.value)
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Pairs</Label>
                      <Input
                        value={editConfig.pairs?.join(", ") ?? ""}
                        onChange={(e) =>
                          updateField(
                            "pairs",
                            e.target.value
                              .split(",")
                              .map((p) => p.trim())
                              .filter(Boolean)
                          )
                        }
                        placeholder="BTCUSDT, ETHUSDT"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>HA Timeframe</Label>
                      <Select
                        value={editConfig.ha_timeframe ?? "1h"}
                        onValueChange={(val) =>
                          updateField("ha_timeframe", val)
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {["5m", "15m", "30m", "1h", "4h", "1d"].map((tf) => (
                            <SelectItem key={tf} value={tf}>
                              {tf}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Entry Timeframe</Label>
                      <Select
                        value={editConfig.entry_timeframe ?? "5m"}
                        onValueChange={(val) =>
                          updateField("entry_timeframe", val)
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {["1m", "5m", "15m", "30m", "1h"].map((tf) => (
                            <SelectItem key={tf} value={tf}>
                              {tf}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                <Separator />

                {/* Risk section */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground">
                    Risk & Capital
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>Stop Loss (%)</Label>
                      <Input
                        type="number"
                        step="0.1"
                        value={editConfig.stop_loss_pct ?? 2.0}
                        onChange={(e) =>
                          updateField(
                            "stop_loss_pct",
                            parseFloat(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Trailing Activation (%)</Label>
                      <Input
                        type="number"
                        step="0.1"
                        value={editConfig.trailing_activation_pct ?? 1.5}
                        onChange={(e) =>
                          updateField(
                            "trailing_activation_pct",
                            parseFloat(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Trailing Distance (%)</Label>
                      <Input
                        type="number"
                        step="0.1"
                        value={editConfig.trailing_distance_pct ?? 0.8}
                        onChange={(e) =>
                          updateField(
                            "trailing_distance_pct",
                            parseFloat(e.target.value)
                          )
                        }
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Trade Capital (USDT)</Label>
                      <Input
                        type="number"
                        step="1"
                        value={editConfig.trade_capital_usdt ?? 100}
                        onChange={(e) =>
                          updateField(
                            "trade_capital_usdt",
                            parseFloat(e.target.value)
                          )
                        }
                      />
                    </div>
                    <div className="flex items-center justify-between py-2">
                      <div>
                        <Label>Use Full Balance</Label>
                        <p className="text-xs text-muted-foreground">
                          Use entire available USDT balance
                        </p>
                      </div>
                      <Switch
                        checked={editConfig.use_full_balance ?? false}
                        onCheckedChange={(val) =>
                          updateField("use_full_balance", val)
                        }
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default BotControl;
