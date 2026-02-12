import {
  activateStrategy,
  deactivateStrategy,
  duplicateStrategy,
  getStrategy,
} from "@/api/strategies";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { formatDate } from "@/lib/utils";
import type { Strategy } from "@/types";
import {
  ArrowLeft,
  BrainCircuit,
  Calendar,
  Copy,
  Edit,
  GitBranch,
  Loader2,
  Shield,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";

const StrategyDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [strategy, setStrategy] = useState<Strategy | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isToggling, setIsToggling] = useState(false);
  const [isDuplicating, setIsDuplicating] = useState(false);

  const fetchStrategy = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const data = await getStrategy(Number(id));
      setStrategy(data);
    } catch {
      toast.error("Strategy not found");
      navigate("/strategies");
    } finally {
      setIsLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchStrategy();
  }, [fetchStrategy]);

  const handleToggle = async () => {
    if (!strategy) return;
    setIsToggling(true);
    try {
      if (strategy.is_active) {
        await deactivateStrategy(strategy.id);
        setStrategy({ ...strategy, is_active: false });
        toast.info("Strategy deactivated");
      } else {
        await activateStrategy(strategy.id);
        setStrategy({ ...strategy, is_active: true });
        toast.success("Strategy activated");
      }
    } catch {
      toast.error("Failed to toggle strategy");
    } finally {
      setIsToggling(false);
    }
  };

  const handleDuplicate = async () => {
    if (!strategy) return;
    setIsDuplicating(true);
    try {
      const copy = await duplicateStrategy(strategy.id);
      toast.success("Strategy duplicated");
      navigate(`/strategies/${copy.id}/edit`);
    } catch {
      toast.error("Failed to duplicate strategy");
    } finally {
      setIsDuplicating(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-64" />
          <Skeleton className="h-64" />
        </div>
      </div>
    );
  }

  if (!strategy) {
    return (
      <div className="text-center py-16">
        <p className="text-destructive mb-4">Strategy not found</p>
        <Link to="/strategies">
          <Button variant="outline">
            <ArrowLeft className="w-4 h-4" />
            Back to Strategies
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link to="/strategies">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">
                {strategy.name}
              </h1>
              <Badge variant={strategy.is_active ? "success" : "secondary"}>
                {strategy.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground mt-0.5">
              Version {strategy.version}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2 mr-3">
            <span className="text-sm text-muted-foreground">
              {strategy.is_active ? "Active" : "Inactive"}
            </span>
            <Switch
              checked={strategy.is_active}
              onCheckedChange={handleToggle}
              disabled={isToggling}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDuplicate}
            disabled={isDuplicating}
          >
            {isDuplicating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
            Duplicate
          </Button>
          <Link to={`/strategies/${strategy.id}/edit`}>
            <Button size="sm">
              <Edit className="w-4 h-4" />
              Edit
            </Button>
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BrainCircuit className="w-4 h-4 text-primary" />
              Overview
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {strategy.description && (
              <p className="text-sm text-muted-foreground">
                {strategy.description}
              </p>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                  <GitBranch className="w-3 h-3" />
                  Timeframe
                </p>
                <p className="font-semibold">{strategy.timeframe}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  Created
                </p>
                <p className="text-sm">{formatDate(strategy.created_at)}</p>
              </div>
            </div>

            {/* Trading pairs */}
            <div>
              <p className="text-xs text-muted-foreground mb-2">
                Trading Pairs
              </p>
              <div className="flex flex-wrap gap-1.5">
                {strategy.pairs.map((pair) => (
                  <Badge key={pair} variant="outline" className="text-xs">
                    {pair}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Required indicators */}
            {strategy.indicators_needed.length > 0 && (
              <div>
                <p className="text-xs text-muted-foreground mb-2">
                  Indicators Used
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {strategy.indicators_needed.map((ind) => (
                    <Badge key={ind} variant="secondary" className="text-xs">
                      {ind}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Risk Management */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="w-4 h-4 text-primary" />
              Risk Management
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Stop Loss</p>
                <p className="text-lg font-bold text-red-600 dark:text-red-400">
                  {strategy.risk.stop_loss_pct}%
                </p>
              </div>
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">Max Position</p>
                <p className="text-lg font-bold">
                  {strategy.risk.max_position_size_pct}%
                </p>
              </div>
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">
                  Trailing Activation
                </p>
                <p className="text-lg font-bold">
                  {strategy.risk.trailing_activation_pct}%
                </p>
              </div>
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">
                  Trailing Distance
                </p>
                <p className="text-lg font-bold">
                  {strategy.risk.trailing_distance_pct}%
                </p>
              </div>
            </div>

            {strategy.risk.take_profit_levels.length > 0 && (
              <div className="mt-4">
                <p className="text-xs text-muted-foreground mb-2">
                  Take Profit Levels
                </p>
                <div className="space-y-1.5">
                  {strategy.risk.take_profit_levels.map((tp, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between bg-green-50/10 rounded p-2 text-sm"
                    >
                      <span className="text-muted-foreground">
                        Level {i + 1}
                      </span>
                      <span className="font-medium text-green-600 dark:text-green-400">
                        {tp.target}% ({tp.pct}% of position)
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Entry Conditions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="w-4 h-4 text-green-500" />
              Entry Conditions ({strategy.entry_conditions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {strategy.entry_conditions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No entry conditions defined.
              </p>
            ) : (
              <div className="space-y-2">
                {strategy.entry_conditions.map((cond, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 bg-green-50/5 border border-green-500/10 rounded-lg p-3"
                  >
                    <Badge variant="success" className="text-xs shrink-0">
                      {i + 1}
                    </Badge>
                    <div className="text-sm">
                      <span className="font-mono font-medium text-foreground">
                        {cond.indicator}
                      </span>
                      <span className="text-muted-foreground">
                        {" "}
                        {cond.operator}{" "}
                      </span>
                      <span className="font-mono text-primary">
                        {cond.value !== null ? String(cond.value) : "null"}
                      </span>
                      {Object.keys(cond.params).length > 0 && (
                        <span className="text-muted-foreground/60 text-xs ml-2">
                          ({JSON.stringify(cond.params)})
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Exit Conditions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Zap className="w-4 h-4 text-red-500" />
              Exit Conditions ({strategy.exit_conditions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {strategy.exit_conditions.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No exit conditions defined.
              </p>
            ) : (
              <div className="space-y-2">
                {strategy.exit_conditions.map((cond, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 bg-red-50/5 border border-red-500/10 rounded-lg p-3"
                  >
                    <Badge variant="danger" className="text-xs shrink-0">
                      {i + 1}
                    </Badge>
                    <div className="text-sm">
                      <span className="font-mono font-medium text-foreground">
                        {cond.indicator}
                      </span>
                      <span className="text-muted-foreground">
                        {" "}
                        {cond.operator}{" "}
                      </span>
                      <span className="font-mono text-primary">
                        {cond.value !== null ? String(cond.value) : "null"}
                      </span>
                      {Object.keys(cond.params).length > 0 && (
                        <span className="text-muted-foreground/60 text-xs ml-2">
                          ({JSON.stringify(cond.params)})
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default StrategyDetail;
