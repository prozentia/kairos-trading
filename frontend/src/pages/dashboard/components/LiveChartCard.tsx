import CandlestickChart from "@/components/charts/CandlestickChart";
import PriceDisplay from "@/components/shared/PriceDisplay";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCandles, useTicker } from "@/hooks/useMarket";
import { cn } from "@/lib/utils";
import { RefreshCw } from "lucide-react";
import { useState } from "react";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;

interface LiveChartCardProps {
  pair?: string;
}

const LiveChartCard = ({ pair = "BTCUSDT" }: LiveChartCardProps) => {
  const [timeframe, setTimeframe] = useState<string>("5m");
  const { candles, isLoading: candlesLoading, refetch } = useCandles(pair, timeframe, 120);
  const { ticker, isLoading: tickerLoading } = useTicker(pair);

  const displayPair = pair.replace("USDT", "/USDT");

  return (
    <Card className="col-span-full xl:col-span-2">
      <CardHeader className="pb-3">
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
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {tf}
                </button>
              ))}
            </div>
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
      </CardHeader>
      <CardContent className="px-2 pb-2">
        {candlesLoading ? (
          <Skeleton className="h-[350px] w-full rounded-lg" />
        ) : (
          <CandlestickChart candles={candles} chartHeight={350} />
        )}
      </CardContent>
    </Card>
  );
};

export default LiveChartCard;
