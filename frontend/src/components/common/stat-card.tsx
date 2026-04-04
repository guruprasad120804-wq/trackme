"use client";

import { cn, formatCurrency, formatPercent, gainColor } from "@/lib/utils";
import { type LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: LucideIcon;
  format?: "currency" | "percent" | "number" | "raw";
  className?: string;
}

export function StatCard({
  title,
  value,
  change,
  changeLabel,
  icon: Icon,
  format = "currency",
  className,
}: StatCardProps) {
  const displayValue = (() => {
    if (format === "raw") return String(value);
    if (format === "percent") return formatPercent(value);
    if (format === "currency") return formatCurrency(value);
    return String(value);
  })();

  return (
    <div
      className={cn(
        "card-hover rounded-xl border border-border bg-card p-5",
        className
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {title}
        </span>
        {Icon && (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber/10">
            <Icon className="h-4 w-4 text-amber" />
          </div>
        )}
      </div>

      <div className="text-2xl font-bold text-foreground">{displayValue}</div>

      {change !== undefined && (
        <div className="mt-2 flex items-center gap-1.5">
          <span
            className={cn(
              "text-sm font-semibold",
              gainColor(change)
            )}
          >
            {formatPercent(change)}
          </span>
          {changeLabel && (
            <span className="text-xs text-muted-foreground">{changeLabel}</span>
          )}
        </div>
      )}
    </div>
  );
}
