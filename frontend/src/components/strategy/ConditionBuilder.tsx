import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDefaultParams } from "@/config/indicators";
import type { Condition } from "@/types";
import { Plus, Zap } from "lucide-react";
import ConditionRow from "./ConditionRow";

interface ConditionBuilderProps {
  label: string;
  conditions: Condition[];
  onChange: (conditions: Condition[]) => void;
  variant: "entry" | "exit";
}

const ConditionBuilder = ({
  label,
  conditions,
  onChange,
  variant,
}: ConditionBuilderProps) => {
  // Add a new empty condition
  const handleAdd = () => {
    const defaultIndicator = variant === "entry" ? "rsi" : "rsi";
    const defaultOp = variant === "entry" ? "below" : "above";
    onChange([
      ...conditions,
      {
        indicator: defaultIndicator,
        params: getDefaultParams(defaultIndicator),
        operator: defaultOp,
        value: variant === "entry" ? 30 : 70,
      },
    ]);
  };

  // Update a condition at index
  const handleUpdate = (index: number, condition: Condition) => {
    const updated = [...conditions];
    updated[index] = condition;
    onChange(updated);
  };

  // Remove a condition at index
  const handleRemove = (index: number) => {
    onChange(conditions.filter((_, i) => i !== index));
  };

  const iconColor = variant === "entry" ? "text-green-500" : "text-red-500";

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center gap-2">
          <Zap className={`w-4 h-4 ${iconColor}`} />
          {label}
          {conditions.length > 0 && (
            <span className="text-sm font-normal text-muted-foreground">
              ({conditions.length})
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {conditions.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            Aucune condition. Cliquez sur "Ajouter" pour commencer.
          </p>
        ) : (
          conditions.map((cond, i) => (
            <ConditionRow
              key={i}
              index={i}
              condition={cond}
              onChange={(c) => handleUpdate(i, c)}
              onRemove={() => handleRemove(i)}
              variant={variant}
            />
          ))
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={handleAdd}
          className="w-full mt-2"
        >
          <Plus className="w-4 h-4" />
          Ajouter une condition
        </Button>
      </CardContent>
    </Card>
  );
};

export default ConditionBuilder;
