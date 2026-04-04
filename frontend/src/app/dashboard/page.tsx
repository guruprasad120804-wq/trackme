"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  Wallet,
  BarChart3,
  PieChart,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { StatCard } from "@/components/common/stat-card";
import { getDashboardSummary, getHoldingsSummary, getTopMovers } from "@/lib/api";
import { cn, formatCurrency, formatPercent, gainColor, compactNumber } from "@/lib/utils";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  PieChart as RePieChart,
  Pie,
  Cell,
} from "recharts";

const PIE_COLORS = ["#F5A623", "#10B981", "#3B82F6", "#8B5CF6", "#EC4899", "#06B6D4", "#F97316"];

export default function DashboardPage() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => getDashboardSummary().then((r) => r.data),
  });

  const { data: holdings } = useQuery({
    queryKey: ["holdings-summary"],
    queryFn: () => getHoldingsSummary().then((r) => r.data),
  });

  const { data: topMovers } = useQuery({
    queryKey: ["top-movers"],
    queryFn: () => getTopMovers().then((r) => r.data),
  });

  // Demo data for chart when no real data
  const performanceData = [
    { month: "Jan", value: 500000, invested: 450000 },
    { month: "Feb", value: 520000, invested: 475000 },
    { month: "Mar", value: 510000, invested: 500000 },
    { month: "Apr", value: 560000, invested: 525000 },
    { month: "May", value: 590000, invested: 550000 },
    { month: "Jun", value: 620000, invested: 575000 },
  ];

  const allocationData = summary?.asset_type_breakdown?.map((b: any, i: number) => ({
    name: b.type.replace("_", " "),
    value: parseFloat(b.allocation_pct),
    color: PIE_COLORS[i % PIE_COLORS.length],
  })) || [
    { name: "Mutual Funds", value: 55, color: PIE_COLORS[0] },
    { name: "Stocks", value: 30, color: PIE_COLORS[1] },
    { name: "ETFs", value: 10, color: PIE_COLORS[2] },
    { name: "Others", value: 5, color: PIE_COLORS[3] },
  ];

  return (
    <div className="min-h-screen">
      <Header title="Dashboard" subtitle="Your portfolio at a glance" />

      <div className="p-6 space-y-6">
        {/* Summary Cards */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          <StatCard
            title="Total Invested"
            value={summary?.total_invested || 0}
            icon={Wallet}
          />
          <StatCard
            title="Current Value"
            value={summary?.current_value || 0}
            change={summary ? parseFloat(summary.total_gain_pct) : undefined}
            changeLabel="all time"
            icon={BarChart3}
          />
          <StatCard
            title="Total Gain/Loss"
            value={summary?.total_gain || 0}
            change={summary ? parseFloat(summary.total_gain_pct) : undefined}
            icon={summary?.total_gain >= 0 ? TrendingUp : TrendingDown}
          />
          <StatCard
            title="Day Change"
            value={summary?.day_change || 0}
            change={summary ? parseFloat(summary.day_change_pct) : undefined}
            changeLabel="today"
            icon={Activity}
          />
        </motion.div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Performance Chart */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-2 rounded-xl border border-border bg-card p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Portfolio Performance</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Invested vs Current Value</p>
              </div>
              <div className="flex gap-2">
                {["1M", "3M", "6M", "1Y", "ALL"].map((period) => (
                  <button
                    key={period}
                    className={cn(
                      "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                      period === "6M"
                        ? "bg-amber/15 text-amber"
                        : "text-muted-foreground hover:bg-secondary"
                    )}
                  >
                    {period}
                  </button>
                ))}
              </div>
            </div>

            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={performanceData}>
                <defs>
                  <linearGradient id="valueGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#F5A623" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#F5A623" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="investedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="month"
                  stroke="#94A3B8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="#94A3B8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => compactNumber(v)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#162036",
                    border: "1px solid #1E3A5F",
                    borderRadius: "8px",
                    color: "#F1F5F9",
                    fontSize: "12px",
                  }}
                  formatter={(value) => [formatCurrency(value as number), ""]}
                />
                <Area
                  type="monotone"
                  dataKey="invested"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  fill="url(#investedGrad)"
                  name="Invested"
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#F5A623"
                  strokeWidth={2}
                  fill="url(#valueGrad)"
                  name="Current Value"
                />
              </AreaChart>
            </ResponsiveContainer>
          </motion.div>

          {/* Asset Allocation Pie */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="rounded-xl border border-border bg-card p-6"
          >
            <h3 className="text-sm font-semibold text-foreground mb-4">Asset Allocation</h3>

            <ResponsiveContainer width="100%" height={200}>
              <RePieChart>
                <Pie
                  data={allocationData}
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {allocationData.map((entry: any, i: number) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
              </RePieChart>
            </ResponsiveContainer>

            <div className="space-y-2 mt-4">
              {allocationData.map((item: any) => (
                <div key={item.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <div
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-muted-foreground capitalize">{item.name}</span>
                  </div>
                  <span className="font-medium text-foreground">{item.value.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Holdings Table + Top Movers */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Holdings List */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="lg:col-span-2 rounded-xl border border-border bg-card"
          >
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className="text-sm font-semibold text-foreground">Top Holdings</h3>
              <a href="/portfolio" className="text-xs text-amber hover:underline">View all</a>
            </div>

            <div className="divide-y divide-border">
              {(holdings || []).slice(0, 6).map((h: any) => (
                <div key={h.id} className="flex items-center justify-between px-5 py-3.5 hover:bg-secondary/50 transition-colors">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{h.asset_name}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {h.asset_type} {h.symbol ? `· ${h.symbol}` : ""}
                    </p>
                  </div>
                  <div className="text-right ml-4">
                    <p className="text-sm font-semibold text-foreground">
                      {formatCurrency(h.current_value)}
                    </p>
                    <p className={cn("text-xs font-medium mt-0.5", gainColor(h.gain_pct))}>
                      {formatPercent(h.gain_pct)}
                    </p>
                  </div>
                </div>
              ))}

              {(!holdings || holdings.length === 0) && (
                <div className="p-10 text-center">
                  <PieChart className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">No holdings yet</p>
                  <p className="text-xs text-muted-foreground mt-1">Import your portfolio to get started</p>
                </div>
              )}
            </div>
          </motion.div>

          {/* Top Movers */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="rounded-xl border border-border bg-card"
          >
            <div className="p-5 border-b border-border">
              <h3 className="text-sm font-semibold text-foreground">Top Movers Today</h3>
            </div>

            <div className="divide-y divide-border">
              {(topMovers || []).map((m: any) => (
                <div key={m.asset_name} className="flex items-center justify-between px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg",
                        m.direction === "up" ? "bg-emerald-500/10" : "bg-red-500/10"
                      )}
                    >
                      {m.direction === "up" ? (
                        <ArrowUpRight className="h-4 w-4 text-emerald-400" />
                      ) : (
                        <ArrowDownRight className="h-4 w-4 text-red-400" />
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-foreground">{m.asset_name}</p>
                      {m.symbol && (
                        <p className="text-xs text-muted-foreground">{m.symbol}</p>
                      )}
                    </div>
                  </div>
                  <span className={cn("text-sm font-semibold", gainColor(m.change_pct))}>
                    {formatPercent(m.change_pct)}
                  </span>
                </div>
              ))}

              {(!topMovers || topMovers.length === 0) && (
                <div className="p-8 text-center">
                  <Activity className="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
                  <p className="text-xs text-muted-foreground">No market data yet</p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
