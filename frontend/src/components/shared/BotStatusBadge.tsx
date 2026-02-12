import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface BotStatusBadgeProps {
  running: boolean;
  mode?: string;
  className?: string;
}

const BotStatusBadge = ({ running, mode, className }: BotStatusBadgeProps) => {
  return (
    <Badge
      variant={running ? "success" : "danger"}
      className={cn("text-xs px-3", className)}
    >
      <span className={cn(
        "w-2 h-2 rounded-full mr-1",
        running ? "bg-green-500 animate-pulse" : "bg-red-500"
      )} />
      {running ? "Running" : "Stopped"}
      {mode && ` (${mode === "dry_run" ? "DRY" : "LIVE"})`}
    </Badge>
  );
};

export default BotStatusBadge;
