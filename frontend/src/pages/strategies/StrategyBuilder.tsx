import {
  createStrategy,
  getStrategy,
  updateStrategy,
  validateStrategy,
} from "@/api/strategies";
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
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { Strategy, StrategyValidation } from "@/types";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Code,
  Loader2,
  Save,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "react-toastify";

const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];
const COMMON_PAIRS = [
  "BTCUSDT",
  "ETHUSDT",
  "SOLUSDT",
  "BNBUSDT",
  "ADAUSDT",
  "DOTUSDT",
  "AVAXUSDT",
  "LINKUSDT",
];

// Default strategy template
const defaultStrategy: Partial<Strategy> = {
  name: "",
  description: "",
  version: "1.0.0",
  pairs: ["BTCUSDT"],
  timeframe: "5m",
  entry_conditions: [],
  exit_conditions: [],
  filters: [],
  risk: {
    stop_loss_pct: 2.0,
    trailing_activation_pct: 1.5,
    trailing_distance_pct: 0.8,
    take_profit_levels: [{ pct: 50, target: 3.0 }],
    max_position_size_pct: 25,
  },
  indicators_needed: [],
  metadata: {},
};

const StrategyBuilder = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = !!id;

  const [strategy, setStrategy] = useState<Partial<Strategy>>(defaultStrategy);
  const [jsonMode, setJsonMode] = useState(false);
  const [jsonInput, setJsonInput] = useState("");
  const [isLoading, setIsLoading] = useState(isEditing);
  const [isSaving, setIsSaving] = useState(false);
  const [validation, setValidation] = useState<StrategyValidation | null>(null);
  const [pairsInput, setPairsInput] = useState("");

  // Load existing strategy for editing
  const fetchStrategy = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const data = await getStrategy(id);
      setStrategy(data);
      setPairsInput(data.pairs.join(", "));
      setJsonInput(JSON.stringify(data, null, 2));
    } catch {
      toast.error("Failed to load strategy");
      navigate("/strategies");
    } finally {
      setIsLoading(false);
    }
  }, [id, navigate]);

  useEffect(() => {
    fetchStrategy();
  }, [fetchStrategy]);

  // Update a field in the strategy
  const updateField = <K extends keyof Strategy>(
    field: K,
    value: Strategy[K]
  ) => {
    setStrategy((prev) => ({ ...prev, [field]: value }));
  };

  // Parse JSON input
  const handleJsonChange = (val: string) => {
    setJsonInput(val);
    try {
      const parsed = JSON.parse(val);
      setStrategy(parsed);
      setPairsInput(parsed.pairs?.join(", ") ?? "");
    } catch {
      // Invalid JSON, user is still typing
    }
  };

  // Toggle JSON mode
  const toggleJsonMode = () => {
    if (!jsonMode) {
      setJsonInput(JSON.stringify(strategy, null, 2));
    }
    setJsonMode(!jsonMode);
  };

  // Handle pairs input
  const handlePairsChange = (val: string) => {
    setPairsInput(val);
    const pairs = val
      .split(",")
      .map((p) => p.trim().toUpperCase())
      .filter(Boolean);
    updateField("pairs", pairs);
  };

  // Quick add pair
  const addPair = (pair: string) => {
    const current = strategy.pairs ?? [];
    if (!current.includes(pair)) {
      const newPairs = [...current, pair];
      updateField("pairs", newPairs);
      setPairsInput(newPairs.join(", "));
    }
  };

  // Validate
  const handleValidate = async () => {
    if (!isEditing || !id) {
      toast.info("Save the strategy first, then validate.");
      return;
    }
    try {
      const result = await validateStrategy(id);
      setValidation(result);
      if (result.valid) {
        toast.success("Strategy is valid!");
      } else {
        toast.warning(`Validation found ${result.errors.length} error(s)`);
      }
    } catch {
      toast.error("Validation failed");
    }
  };

  // Save
  const handleSave = async () => {
    if (!strategy.name?.trim()) {
      toast.error("Strategy name is required");
      return;
    }
    setIsSaving(true);
    try {
      if (isEditing && id) {
        await updateStrategy(id, strategy);
        toast.success("Strategy updated");
      } else {
        const created = await createStrategy(strategy);
        toast.success("Strategy created");
        navigate(`/strategies/${created.id}`);
      }
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Failed to save strategy"
      );
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[400px]" />
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
          <h1 className="text-2xl font-bold text-foreground">
            {isEditing ? "Edit Strategy" : "New Strategy"}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={toggleJsonMode}>
            <Code className="w-4 h-4" />
            {jsonMode ? "Form Mode" : "JSON Mode"}
          </Button>
          {isEditing && (
            <Button variant="outline" size="sm" onClick={handleValidate}>
              <ShieldCheck className="w-4 h-4" />
              Validate
            </Button>
          )}
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            {isEditing ? "Update" : "Create"}
          </Button>
        </div>
      </div>

      {/* Validation results */}
      {validation && (
        <Card
          className={
            validation.valid
              ? "border-green-500/30 bg-green-50/5"
              : "border-red-500/30 bg-red-50/5"
          }
        >
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              {validation.valid ? (
                <CheckCircle2 className="w-5 h-5 text-green-600" />
              ) : (
                <XCircle className="w-5 h-5 text-red-600" />
              )}
              <span className="font-semibold">
                {validation.valid
                  ? "Strategy is valid"
                  : "Validation errors found"}
              </span>
            </div>
            {validation.errors.map((err, i) => (
              <p key={i} className="text-sm text-red-600 ml-7">
                {err}
              </p>
            ))}
            {validation.warnings.map((warn, i) => (
              <p
                key={i}
                className="text-sm text-amber-600 ml-7 flex items-center gap-1"
              >
                <AlertTriangle className="w-3 h-3" />
                {warn}
              </p>
            ))}
          </CardContent>
        </Card>
      )}

      {/* JSON editor mode */}
      {jsonMode ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">JSON Editor</CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={jsonInput}
              onChange={(e) => handleJsonChange(e.target.value)}
              className="font-mono text-sm min-h-[500px]"
              placeholder="Paste or edit the strategy JSON here..."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* General settings */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">General</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Strategy Name *</Label>
                <Input
                  id="name"
                  value={strategy.name ?? ""}
                  onChange={(e) => updateField("name", e.target.value)}
                  placeholder="e.g. RSI Momentum Scalper"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={strategy.description ?? ""}
                  onChange={(e) => updateField("description", e.target.value)}
                  placeholder="Describe what this strategy does..."
                  rows={3}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="version">Version</Label>
                  <Input
                    id="version"
                    value={strategy.version ?? "1.0.0"}
                    onChange={(e) => updateField("version", e.target.value)}
                    placeholder="1.0.0"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Timeframe</Label>
                  <Select
                    value={strategy.timeframe ?? "5m"}
                    onValueChange={(val) => updateField("timeframe", val)}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TIMEFRAMES.map((tf) => (
                        <SelectItem key={tf} value={tf}>
                          {tf}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pairs selection */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Trading Pairs</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Selected Pairs</Label>
                <Input
                  value={pairsInput}
                  onChange={(e) => handlePairsChange(e.target.value)}
                  placeholder="BTCUSDT, ETHUSDT, ..."
                />
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-2">
                  Quick add:
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {COMMON_PAIRS.map((pair) => (
                    <Badge
                      key={pair}
                      variant={
                        strategy.pairs?.includes(pair) ? "default" : "outline"
                      }
                      className="cursor-pointer text-xs"
                      onClick={() => addPair(pair)}
                    >
                      {pair}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Risk management */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Risk Management</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Stop Loss (%)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={strategy.risk?.stop_loss_pct ?? 2.0}
                    onChange={(e) =>
                      updateField("risk", {
                        ...strategy.risk!,
                        stop_loss_pct: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Max Position (%)</Label>
                  <Input
                    type="number"
                    step="1"
                    value={strategy.risk?.max_position_size_pct ?? 25}
                    onChange={(e) =>
                      updateField("risk", {
                        ...strategy.risk!,
                        max_position_size_pct: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Trailing Activation (%)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={strategy.risk?.trailing_activation_pct ?? 1.5}
                    onChange={(e) =>
                      updateField("risk", {
                        ...strategy.risk!,
                        trailing_activation_pct: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>Trailing Distance (%)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    value={strategy.risk?.trailing_distance_pct ?? 0.8}
                    onChange={(e) =>
                      updateField("risk", {
                        ...strategy.risk!,
                        trailing_distance_pct: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Conditions preview (JSON) */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Conditions (JSON)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Entry Conditions</Label>
                <Textarea
                  className="font-mono text-xs min-h-[120px]"
                  value={JSON.stringify(
                    strategy.entry_conditions ?? [],
                    null,
                    2
                  )}
                  onChange={(e) => {
                    try {
                      updateField(
                        "entry_conditions",
                        JSON.parse(e.target.value)
                      );
                    } catch {
                      // Invalid JSON while typing
                    }
                  }}
                  placeholder="[]"
                />
              </div>
              <div className="space-y-2">
                <Label>Exit Conditions</Label>
                <Textarea
                  className="font-mono text-xs min-h-[120px]"
                  value={JSON.stringify(
                    strategy.exit_conditions ?? [],
                    null,
                    2
                  )}
                  onChange={(e) => {
                    try {
                      updateField(
                        "exit_conditions",
                        JSON.parse(e.target.value)
                      );
                    } catch {
                      // Invalid JSON while typing
                    }
                  }}
                  placeholder="[]"
                />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default StrategyBuilder;
