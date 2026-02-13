import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  CATEGORY_LABELS,
  getDefaultParams,
  getIndicator,
  getIndicatorsByCategory,
  type IndicatorCategory,
  type ParamDef,
} from "@/config/indicators";
import type { Condition } from "@/types";
import { ChevronDown, ChevronUp, Settings2, Trash2 } from "lucide-react";
import { useState } from "react";

interface ConditionRowProps {
  index: number;
  condition: Condition;
  onChange: (condition: Condition) => void;
  onRemove: () => void;
  variant: "entry" | "exit";
}

const ConditionRow = ({
  index,
  condition,
  onChange,
  onRemove,
  variant,
}: ConditionRowProps) => {
  const [showParams, setShowParams] = useState(false);
  const grouped = getIndicatorsByCategory();
  const indicatorDef = getIndicator(condition.indicator);
  const operators = indicatorDef?.operators ?? [];
  const currentOp = operators.find((o) => o.key === condition.operator);

  // Handle indicator change — reset operator and params
  const handleIndicatorChange = (key: string) => {
    const newInd = getIndicator(key);
    const firstOp = newInd?.operators[0]?.key ?? "";
    onChange({
      indicator: key,
      params: getDefaultParams(key),
      operator: firstOp,
      value: null,
    });
  };

  // Handle operator change
  const handleOperatorChange = (op: string) => {
    const opDef = operators.find((o) => o.key === op);
    onChange({
      ...condition,
      operator: op,
      value: opDef?.needsValue ? condition.value : null,
    });
  };

  // Handle value change
  const handleValueChange = (val: string) => {
    const num = parseFloat(val);
    onChange({
      ...condition,
      value: isNaN(num) ? null : num,
    });
  };

  // Handle param change
  const handleParamChange = (paramKey: string, val: string, paramDef: ParamDef) => {
    const parsed = paramDef.type === "number" ? parseFloat(val) : val;
    onChange({
      ...condition,
      params: { ...condition.params, [paramKey]: parsed },
    });
  };

  const borderColor =
    variant === "entry"
      ? "border-green-500/20 hover:border-green-500/40"
      : "border-red-500/20 hover:border-red-500/40";

  return (
    <div className={`rounded-lg border ${borderColor} bg-card transition-colors`}>
      {/* Main row */}
      <div className="flex items-center gap-2 p-3">
        <Badge
          variant={variant === "entry" ? "success" : "danger"}
          className="text-xs shrink-0 w-6 h-6 flex items-center justify-center p-0"
        >
          {index + 1}
        </Badge>

        {/* Indicator select */}
        <select
          value={condition.indicator}
          onChange={(e) => handleIndicatorChange(e.target.value)}
          className="h-9 rounded-md border border-input bg-background px-2 text-sm min-w-[140px] focus:outline-none focus:ring-1 focus:ring-ring"
        >
          <option value="">-- Indicateur --</option>
          {(Object.entries(grouped) as [IndicatorCategory, typeof grouped.trend][]).map(
            ([cat, indicators]) => (
              <optgroup key={cat} label={CATEGORY_LABELS[cat]}>
                {indicators.map((ind) => (
                  <option key={ind.key} value={ind.key}>
                    {ind.name}
                  </option>
                ))}
              </optgroup>
            )
          )}
        </select>

        {/* Operator select */}
        <select
          value={condition.operator}
          onChange={(e) => handleOperatorChange(e.target.value)}
          className="h-9 rounded-md border border-input bg-background px-2 text-sm min-w-[160px] focus:outline-none focus:ring-1 focus:ring-ring"
          disabled={operators.length === 0}
        >
          {operators.length === 0 && (
            <option value="">-- Operateur --</option>
          )}
          {operators.map((op) => (
            <option key={op.key} value={op.key}>
              {op.label}
            </option>
          ))}
        </select>

        {/* Value input (only if operator needs it) */}
        {currentOp?.needsValue && (
          <Input
            type="number"
            step="any"
            value={condition.value ?? ""}
            onChange={(e) => handleValueChange(e.target.value)}
            placeholder="Valeur"
            className="w-24 h-9"
          />
        )}

        {/* Params toggle */}
        {indicatorDef && indicatorDef.params.length > 0 && (
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={() => setShowParams(!showParams)}
            title="Parametres"
          >
            <Settings2 className="w-3.5 h-3.5" />
            {showParams ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
          </Button>
        )}

        <div className="flex-1" />

        {/* Remove */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onRemove}
          className="text-destructive hover:text-destructive shrink-0"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* Params panel (collapsible) */}
      {showParams && indicatorDef && indicatorDef.params.length > 0 && (
        <div className="border-t border-border px-3 py-2 bg-muted/30">
          <div className="flex flex-wrap gap-3">
            {indicatorDef.params.map((p) => (
              <div key={p.key} className="space-y-1">
                <Label className="text-[11px] text-muted-foreground">
                  {p.label}
                </Label>
                {p.type === "select" ? (
                  <select
                    value={String(condition.params[p.key] ?? p.default)}
                    onChange={(e) => handleParamChange(p.key, e.target.value, p)}
                    className="h-8 rounded-md border border-input bg-background px-2 text-xs w-24 focus:outline-none focus:ring-1 focus:ring-ring"
                  >
                    {p.options?.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                ) : (
                  <Input
                    type="number"
                    step={p.step ?? 1}
                    min={p.min}
                    max={p.max}
                    value={condition.params[p.key] as number ?? p.default}
                    onChange={(e) => handleParamChange(p.key, e.target.value, p)}
                    className="w-20 h-8 text-xs"
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ConditionRow;
