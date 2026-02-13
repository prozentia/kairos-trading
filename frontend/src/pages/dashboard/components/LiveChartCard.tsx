import CandlestickChart from "@/components/charts/CandlestickChart";
import PriceDisplay from "@/components/shared/PriceDisplay";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCandles, useTicker } from "@/hooks/useMarket";
import { toHeikinAshi } from "@/lib/heikinAshi";
import { cn } from "@/lib/utils";
import { CandlestickChart as CandlestickIcon, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";

const TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h", "4h", "1d"] as const;

const DEFAULT_PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"];

interface LiveChartCardProps {
  pair?: string;
  pairs?: string[];
  onPairChange?: (pair: string) => void;
}

const LiveChartCard = ({
  pair = "BTCUSDT",
  pairs,
  onPairChange,
}: LiveChartCardProps) => {
  const [timeframe, setTimeframe] = useState<string>("5m");
  const [showHA, setShowHA] = useState(false);
  const { candles, isLoading: candlesLoading, refetch } = useCandles(pair, timeframe, 120);
  const { ticker, isLoading: tickerLoading } = useTicker(pair);

  const displayPair = pair.replace("USDT", "/USDT");
  const availablePairs = pairs && pairs.length > 0 ? pairs : DEFAULT_PAIRS;

  // Convert to Heikin Ashi if toggle is active
  const displayCandles = useMemo(
    () => (showHA ? toHeikinAshi(candles) : candles),
    [candles, showHA],
  );

  return (
    <Card className="col-span-full xl:col-span-2">
      <CardHeader className="pb-3">
        <div className="flex flex-col gap-3">
          {/* Row 1: Pair selector tabs */}
          <div className="flex items-center gap-2 overflow-x-auto">
            <div className="flex items-center bg-muted rounded-lg p-0.5">
              {availablePairs.map((p) => (
                <button
                  key={p}
                  onClick={() => onPairChange?.(p)}
                  className={cn(
                    "px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap",
                    pair === p
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {p.replace("USDT", "")}
                </button>
              ))}
            </div>
          </div>

          {/* Row 2: Pair name + price + timeframe + HA toggle + refresh */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <CardTitle className="text-lg">{displayPair}</CardTitle>
              {tickerLoading ? (
                <Skeleton className="h-7 w-40" />
              ) : ticker ? (
                <PriceDisplay
                  price={ticker.price}
                  change={ticker.change_24h_pct}
                  size="md"
                />
              ) : null}
            </div>
            <div className="flex items-center gap-2">
              {/* Timeframe selector */}
              <div className="flex items-center bg-muted rounded-lg p-0.5">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={cn(
                      "px-2.5 py-1 text-xs font-medium rounded-md transition-colors",
                      timeframe === tf
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {tf}
                  </button>
                ))}
              </div>
              {/* Heikin Ashi toggle */}
              <Button
                variant={showHA ? "default" : "ghost"}
                size="icon-sm"
                onClick={() => setShowHA(!showHA)}
                title={showHA ? "Heikin Ashi activé" : "Activer Heikin Ashi"}
                className={cn(showHA && "bg-amber-600 hover:bg-amber-700 text-white")}
              >
                <CandlestickIcon className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => refetch()}
                title="Refresh chart"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-2 pb-2">
        {candlesLoading ? (
          <Skeleton className="h-[350px] w-full rounded-lg" />
        ) : (
          <CandlestickChart candles={displayCandles} chartHeight={350} />
        )}
        {showHA && (
          <div className="text-center text-xs text-muted-foreground mt-1">
            Heikin Ashi
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default LiveChartCard;
