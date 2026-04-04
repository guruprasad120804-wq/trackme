"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Bell,
  Plus,
  Trash2,
  ToggleLeft,
  ToggleRight,
  TrendingUp,
  TrendingDown,
  Wallet,
  Clock,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn, formatCurrency } from "@/lib/utils";
import { getAlerts, getAlertHistory, toggleAlert, deleteAlert } from "@/lib/api";

const CONDITION_ICONS: Record<string, any> = {
  price_above: TrendingUp,
  price_below: TrendingDown,
  portfolio_value_above: Wallet,
  portfolio_value_below: Wallet,
  sip_reminder: Clock,
};

const CONDITION_LABELS: Record<string, string> = {
  price_above: "Price Above",
  price_below: "Price Below",
  gain_pct_above: "Gain % Above",
  loss_pct_above: "Loss % Above",
  portfolio_value_above: "Portfolio Value Above",
  portfolio_value_below: "Portfolio Value Below",
  day_change_pct: "Day Change %",
  sip_reminder: "SIP Reminder",
  custom: "Custom Rule",
};

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<"active" | "history">("active");

  const { data: alerts } = useQuery({
    queryKey: ["alerts"],
    queryFn: () => getAlerts().then((r) => r.data),
  });

  const { data: history } = useQuery({
    queryKey: ["alert-history"],
    queryFn: () => getAlertHistory().then((r) => r.data),
    enabled: tab === "history",
  });

  const toggleMutation = useMutation({
    mutationFn: (id: string) => toggleAlert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteAlert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
  });

  return (
    <div className="min-h-screen">
      <Header title="Alerts" subtitle="Price alerts, triggers & reminders" />

      <div className="p-6 space-y-6">
        {/* Top bar */}
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            {(["active", "history"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  "px-4 py-2 text-sm font-medium rounded-lg transition-colors capitalize",
                  tab === t
                    ? "bg-amber/15 text-amber"
                    : "text-muted-foreground hover:bg-secondary"
                )}
              >
                {t}
              </button>
            ))}
          </div>

          <Button className="bg-amber hover:bg-amber-dark text-navy font-semibold" size="sm">
            <Plus className="h-4 w-4 mr-1" />
            Create Alert
          </Button>
        </div>

        {/* Active Alerts */}
        {tab === "active" && (
          <div className="space-y-3">
            {(alerts || []).map((alert: any, i: number) => {
              const Icon = CONDITION_ICONS[alert.condition] || Bell;
              return (
                <motion.div
                  key={alert.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex items-center justify-between rounded-xl border border-border bg-card p-5 card-hover"
                >
                  <div className="flex items-center gap-4">
                    <div className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg",
                      alert.is_active ? "bg-amber/10" : "bg-secondary"
                    )}>
                      <Icon className={cn("h-5 w-5", alert.is_active ? "text-amber" : "text-muted-foreground")} />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-foreground">{alert.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {CONDITION_LABELS[alert.condition] || alert.condition}
                        {alert.threshold && ` — ${formatCurrency(alert.threshold)}`}
                        {alert.asset_name && ` · ${alert.asset_name}`}
                      </p>
                      <div className="flex gap-1.5 mt-1.5">
                        {(alert.channels || []).map((ch: string) => (
                          <Badge
                            key={ch}
                            variant="outline"
                            className="text-[9px] px-1.5 py-0 capitalize border-border text-muted-foreground"
                          >
                            {ch}
                          </Badge>
                        ))}
                        {alert.is_recurring && (
                          <Badge variant="outline" className="text-[9px] px-1.5 py-0 border-amber/30 text-amber">
                            Recurring
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleMutation.mutate(alert.id)}
                      className="p-2 rounded-lg hover:bg-secondary transition-colors"
                    >
                      {alert.is_active ? (
                        <ToggleRight className="h-6 w-6 text-amber" />
                      ) : (
                        <ToggleLeft className="h-6 w-6 text-muted-foreground" />
                      )}
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(alert.id)}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </motion.div>
              );
            })}

            {(!alerts || alerts.length === 0) && (
              <div className="rounded-xl border border-border bg-card p-12 text-center">
                <Bell className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">No alerts set up yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Create price alerts, portfolio triggers, or SIP reminders
                </p>
              </div>
            )}
          </div>
        )}

        {/* Alert History */}
        {tab === "history" && (
          <div className="rounded-xl border border-border bg-card divide-y divide-border">
            {(history || []).map((h: any) => (
              <div key={h.id} className="flex items-center justify-between px-5 py-4">
                <div>
                  <p className="text-sm font-medium text-foreground">{h.alert_name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{h.message}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">{h.triggered_at}</p>
                  {h.channel_used && (
                    <Badge variant="outline" className="text-[9px] mt-1 capitalize">{h.channel_used}</Badge>
                  )}
                </div>
              </div>
            ))}

            {(!history || history.length === 0) && (
              <div className="p-8 text-center">
                <p className="text-sm text-muted-foreground">No alert history</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
