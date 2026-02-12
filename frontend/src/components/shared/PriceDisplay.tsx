import { cn } from "@/lib/utils";
import { formatCurrency, formatPct } from "@/lib/utils";

interface PriceDisplayProps {
  price: number;
  change?: number;
  className?: string;
  size?: "sm" | "md" | "lg";
}

const PriceDisplay = ({ price, change, className, size = "md" }: PriceDisplayProps) => {
  const sizeClasses = {
    sm: "text-sm",
    md: "text-lg",
    lg: "text-2xl",
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <span className={cn("font-bold", sizeClasses[size])}>
        {formatCurrency(price)}
      </span>
      {change !== undefined && (
        <span
          className={cn(
            "text-sm font-medium px-1.5 py-0.5 rounded",
            change >= 0
              ? "text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-600/20"
              : "text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-600/20"
          )}
        >
          {formatPct(change)}
        </span>
      )}
    </div>
  );
};

export default PriceDisplay;
