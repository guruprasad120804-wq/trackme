"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Briefcase, Search, Filter, ArrowUpDown } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn, formatCurrency, formatPercent, formatNumber, gainColor } from "@/lib/utils";
import { getPortfolios, getHoldingsSummary } from "@/lib/api";

const ASSET_TYPES = [
  { label: "All", value: "" },
  { label: "Stocks", value: "stock" },
  { label: "Mutual Funds", value: "mutual_fund" },
  { label: "ETFs", value: "etf" },
  { label: "Gold", value: "gold" },
  { label: "Others", value: "other" },
];

export default function PortfolioPage() {
  const [filter, setFilter] = useState("");
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("current_value");

  const { data: portfolios } = useQuery({
    queryKey: ["portfolios"],
    queryFn: () => getPortfolios().then((r) => r.data),
  });

  const { data: holdings, isLoading } = useQuery({
    queryKey: ["holdings", filter, sortBy],
    queryFn: () =>
      getHoldingsSummary({
        ...(filter ? { asset_type: filter } : {}),
        sort_by: sortBy,
        sort_order: "desc",
      }).then((r) => r.data),
  });

  const filteredHoldings = (holdings || []).filter((h: any) =>
    h.asset_name.toLowerCase().includes(search.toLowerCase()) ||
    (h.symbol && h.symbol.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="min-h-screen">
      <Header title="Portfolio" subtitle="Your investment holdings" />

      <div className="p-6 space-y-6">
        {/* Portfolio summary cards */}
        {portfolios && portfolios.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {portfolios.map((p: any) => (
              <div
                key={p.id}
                className="rounded-xl border border-border bg-card p-5 card-hover"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Briefcase className="h-4 w-4 text-amber" />
                    <span className="text-sm font-semibold text-foreground">{p.name}</span>
                  </div>
                  {p.is_default && (
                    <Badge variant="outline" className="text-[10px] text-amber border-amber/30">
                      Default
                    </Badge>
                  )}
                </div>
                <p className="text-xl font-bold text-foreground">{formatCurrency(p.current_value)}</p>
                <p className={cn("text-sm font-medium mt-1", gainColor(p.total_gain_pct))}>
                  {formatCurrency(p.total_gain)} ({formatPercent(p.total_gain_pct)})
                </p>
                <p className="text-xs text-muted-foreground mt-2">{p.holdings_count} holdings</p>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search holdings..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 bg-secondary border-border"
            />
          </div>

          <div className="flex gap-2 flex-wrap">
            {ASSET_TYPES.map((type) => (
              <button
                key={type.value}
                onClick={() => setFilter(type.value)}
                className={cn(
                  "px-3 py-1.5 text-xs font-medium rounded-lg transition-colors",
                  filter === type.value
                    ? "bg-amber/15 text-amber border border-amber/30"
                    : "bg-secondary text-muted-foreground hover:text-foreground border border-transparent"
                )}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>

        {/* Holdings table */}
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="text-left px-5 py-3 font-medium">Asset</th>
                <th className="text-right px-5 py-3 font-medium">Qty</th>
                <th className="text-right px-5 py-3 font-medium">Avg Cost</th>
                <th className="text-right px-5 py-3 font-medium">CMP</th>
                <th className="text-right px-5 py-3 font-medium">Invested</th>
                <th className="text-right px-5 py-3 font-medium">Current</th>
                <th className="text-right px-5 py-3 font-medium">P&L</th>
                <th className="text-right px-5 py-3 font-medium">Day</th>
                <th className="text-right px-5 py-3 font-medium">Alloc %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredHoldings.map((h: any, i: number) => (
                <motion.tr
                  key={h.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.03 }}
                  className="hover:bg-secondary/50 transition-colors cursor-pointer"
                >
                  <td className="px-5 py-3.5">
                    <div>
                      <p className="text-sm font-medium text-foreground">{h.asset_name}</p>
                      <p className="text-[11px] text-muted-foreground">
                        {h.asset_type.replace("_", " ")} {h.symbol ? `· ${h.symbol}` : ""}
                      </p>
                    </div>
                  </td>
                  <td className="text-right px-5 py-3.5 text-sm text-foreground">
                    {formatNumber(h.quantity, 3)}
                  </td>
                  <td className="text-right px-5 py-3.5 text-sm text-foreground">
                    {formatCurrency(h.avg_cost, 2)}
                  </td>
                  <td className="text-right px-5 py-3.5 text-sm text-foreground">
                    {formatCurrency(h.current_price, 2)}
                  </td>
                  <td className="text-right px-5 py-3.5 text-sm text-foreground">
                    {formatCurrency(h.invested)}
                  </td>
                  <td className="text-right px-5 py-3.5 text-sm font-semibold text-foreground">
                    {formatCurrency(h.current_value)}
                  </td>
                  <td className="text-right px-5 py-3.5">
                    <div className={cn("text-sm font-semibold", gainColor(h.gain))}>
                      {formatCurrency(h.gain)}
                    </div>
                    <div className={cn("text-[11px]", gainColor(h.gain_pct))}>
                      {formatPercent(h.gain_pct)}
                    </div>
                  </td>
                  <td className={cn("text-right px-5 py-3.5 text-sm font-medium", gainColor(h.day_change_pct))}>
                    {formatPercent(h.day_change_pct)}
                  </td>
                  <td className="text-right px-5 py-3.5 text-sm text-muted-foreground">
                    {parseFloat(h.allocation_pct).toFixed(1)}%
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>

          {filteredHoldings.length === 0 && !isLoading && (
            <div className="p-12 text-center">
              <Briefcase className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No holdings found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
