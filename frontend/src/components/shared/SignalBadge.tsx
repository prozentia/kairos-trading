import { Badge } from "@/components/ui/badge";
import { ArrowDown, ArrowUp } from "lucide-react";

interface SignalBadgeProps {
  side: "BUY" | "SELL";
}

const SignalBadge = ({ side }: SignalBadgeProps) => {
  if (side === "BUY") {
    return (
      <Badge variant="success" className="text-xs px-2 py-0.5">
        <ArrowUp className="w-3 h-3" />
        BUY
      </Badge>
    );
  }

  return (
    <Badge variant="danger" className="text-xs px-2 py-0.5">
      <ArrowDown className="w-3 h-3" />
      SELL
    </Badge>
  );
};

export default SignalBadge;
