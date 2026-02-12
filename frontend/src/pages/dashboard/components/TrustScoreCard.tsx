import TrustScoreGauge from "@/components/charts/TrustScoreGauge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Shield } from "lucide-react";

interface TrustScoreCardProps {
  score: number;
  isLoading: boolean;
}

function getTrustInfo(score: number) {
  if (score < 40)
    return {
      label: "CRAWL",
      color: "text-red-600 dark:text-red-400",
      bg: "bg-red-100 dark:bg-red-600/20",
      description: "Dry run only. Build trust through consistent wins.",
      capital: "0%",
    };
  if (score < 65)
    return {
      label: "WALK",
      color: "text-amber-600 dark:text-amber-400",
      bg: "bg-amber-100 dark:bg-amber-600/20",
      description: "Supervised live trading. 25% capital allocation.",
      capital: "25%",
    };
  if (score < 80)
    return {
      label: "RUN",
      color: "text-blue-600 dark:text-blue-400",
      bg: "bg-blue-100 dark:bg-blue-600/20",
      description: "Semi-autonomous mode. 50% capital allocation.",
      capital: "50%",
    };
  return {
    label: "SPRINT",
    color: "text-green-600 dark:text-green-400",
    bg: "bg-green-100 dark:bg-green-600/20",
    description: "Fully autonomous. 80% capital allocation.",
    capital: "80%",
  };
}

const TrustScoreCard = ({ score, isLoading }: TrustScoreCardProps) => {
  const trust = getTrustInfo(score);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Shield className="w-4 h-4 text-primary" />
          Trust Score
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-[200px] w-full" />
            <Skeleton className="h-4 w-full" />
          </div>
        ) : (
          <div className="space-y-3">
            <TrustScoreGauge score={score} chartHeight={180} />

            {/* Trust level details */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold ${trust.color} ${trust.bg}`}
                >
                  {trust.label}
                </span>
                <span className="text-xs text-muted-foreground">
                  Capital: <strong>{trust.capital}</strong>
                </span>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {trust.description}
              </p>
            </div>

            {/* Score breakdown bar */}
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>CRAWL</span>
                <span>WALK</span>
                <span>RUN</span>
                <span>SPRINT</span>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    width: `${score}%`,
                    background: `linear-gradient(90deg, #ef4444 0%, #f59e0b 40%, #3b82f6 65%, #22c55e 100%)`,
                  }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted-foreground/60">
                <span>0</span>
                <span>40</span>
                <span>65</span>
                <span>80</span>
                <span>100</span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default TrustScoreCard;
