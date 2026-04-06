"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Shield,
  Plus,
  Trash2,
  Calendar,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { cn, formatCurrency } from "@/lib/utils";
import { getInsurancePolicies, createInsurancePolicy, deleteInsurancePolicy } from "@/lib/api";

const POLICY_TYPES = [
  { value: "term", label: "Term Life" },
  { value: "endowment", label: "Endowment" },
  { value: "ulip", label: "ULIP" },
  { value: "health", label: "Health" },
  { value: "vehicle", label: "Vehicle" },
  { value: "travel", label: "Travel" },
];

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-400",
  lapsed: "bg-red-500/15 text-red-400",
  matured: "bg-amber/15 text-amber",
  surrendered: "bg-gray-500/15 text-gray-400",
};

export default function InsurancePage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    policy_number: "",
    provider: "",
    type: "term",
    sum_assured: "",
    premium_amount: "",
    premium_frequency: "yearly",
    next_premium_date: "",
    maturity_date: "",
    start_date: "",
    nominee: "",
    notes: "",
  });

  const { data: policies, isLoading } = useQuery({
    queryKey: ["insurance"],
    queryFn: () => getInsurancePolicies().then((r) => r.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => createInsurancePolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["insurance"] });
      setShowAdd(false);
      setForm({
        policy_number: "", provider: "", type: "term", sum_assured: "",
        premium_amount: "", premium_frequency: "yearly", next_premium_date: "",
        maturity_date: "", start_date: "", nominee: "", notes: "",
      });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteInsurancePolicy(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["insurance"] }),
  });

  const handleSubmit = () => {
    createMutation.mutate({
      ...form,
      sum_assured: parseFloat(form.sum_assured) || 0,
      premium_amount: parseFloat(form.premium_amount) || 0,
      next_premium_date: form.next_premium_date || null,
      maturity_date: form.maturity_date || null,
      start_date: form.start_date || null,
    });
  };

  const isDueSoon = (dateStr: string | null) => {
    if (!dateStr) return false;
    const d = new Date(dateStr);
    const now = new Date();
    const diff = (d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
    return diff >= 0 && diff <= 7;
  };

  const isOverdue = (dateStr: string | null) => {
    if (!dateStr) return false;
    return new Date(dateStr) < new Date();
  };

  return (
    <div className="min-h-screen">
      <Header title="Insurance" subtitle="Track your insurance policies" />

      <div className="p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">
              {(policies || []).length} {(policies || []).length === 1 ? "policy" : "policies"}
            </p>
          </div>
          <Button onClick={() => setShowAdd(true)} className="bg-amber hover:bg-amber-dark text-navy font-semibold" size="sm">
            <Plus className="h-4 w-4 mr-1" />
            Add Policy
          </Button>
        </div>

        {/* Policies List */}
        <div className="space-y-3">
          {(policies || []).map((p: any, i: number) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-xl border border-border bg-card p-5 card-hover"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber/10">
                    <Shield className="h-5 w-5 text-amber" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-semibold text-foreground">{p.provider}</p>
                      <Badge className={cn("text-[10px] px-1.5 py-0 capitalize", STATUS_COLORS[p.status] || STATUS_COLORS.active)}>
                        {p.status}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {POLICY_TYPES.find((t) => t.value === p.type)?.label || p.type} &middot; #{p.policy_number}
                    </p>
                    <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                      <span>Cover: {formatCurrency(parseFloat(p.sum_assured))}</span>
                      <span>Premium: {formatCurrency(parseFloat(p.premium_amount))}/{p.premium_frequency}</span>
                    </div>
                    {p.next_premium_date && (
                      <div className={cn(
                        "flex items-center gap-1 mt-2 text-xs",
                        isOverdue(p.next_premium_date) ? "text-red-400" :
                        isDueSoon(p.next_premium_date) ? "text-amber" : "text-muted-foreground"
                      )}>
                        {(isOverdue(p.next_premium_date) || isDueSoon(p.next_premium_date)) && (
                          <AlertTriangle className="h-3 w-3" />
                        )}
                        <Calendar className="h-3 w-3" />
                        Next premium: {new Date(p.next_premium_date).toLocaleDateString()}
                        {isOverdue(p.next_premium_date) && " (overdue)"}
                        {isDueSoon(p.next_premium_date) && " (due soon)"}
                      </div>
                    )}
                    {p.nominee && (
                      <p className="text-[11px] text-muted-foreground mt-1">Nominee: {p.nominee}</p>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => deleteMutation.mutate(p.id)}
                  className="p-2 rounded-lg hover:bg-red-500/10 text-muted-foreground hover:text-red-400 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </motion.div>
          ))}

          {(!policies || policies.length === 0) && !isLoading && (
            <div className="rounded-xl border border-border bg-card p-12 text-center">
              <Shield className="h-12 w-12 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No insurance policies tracked</p>
              <p className="text-xs text-muted-foreground mt-1">
                Add your policies to track premiums, coverage, and renewal dates
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Add Policy Modal */}
      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="sm:max-w-md bg-card border-border">
          <DialogHeader>
            <DialogTitle className="text-foreground">Add Insurance Policy</DialogTitle>
            <DialogDescription>Track your policy details and premium dates</DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2 max-h-[60vh] overflow-y-auto">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Provider</label>
                <Input className="mt-1 bg-secondary border-border" placeholder="LIC, HDFC Life..." value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Policy Number</label>
                <Input className="mt-1 bg-secondary border-border" placeholder="Policy #" value={form.policy_number} onChange={(e) => setForm({ ...form, policy_number: e.target.value })} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Type</label>
                <select className="mt-1 w-full rounded-lg border border-border bg-secondary px-3 py-2 text-sm text-foreground" value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
                  {POLICY_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Sum Assured (₹)</label>
                <Input type="number" className="mt-1 bg-secondary border-border" placeholder="1000000" value={form.sum_assured} onChange={(e) => setForm({ ...form, sum_assured: e.target.value })} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Premium (₹)</label>
                <Input type="number" className="mt-1 bg-secondary border-border" placeholder="12000" value={form.premium_amount} onChange={(e) => setForm({ ...form, premium_amount: e.target.value })} />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Frequency</label>
                <select className="mt-1 w-full rounded-lg border border-border bg-secondary px-3 py-2 text-sm text-foreground" value={form.premium_frequency} onChange={(e) => setForm({ ...form, premium_frequency: e.target.value })}>
                  <option value="monthly">Monthly</option>
                  <option value="quarterly">Quarterly</option>
                  <option value="half_yearly">Half Yearly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-muted-foreground">Next Premium Date</label>
                <Input type="date" className="mt-1 bg-secondary border-border" value={form.next_premium_date} onChange={(e) => setForm({ ...form, next_premium_date: e.target.value })} />
              </div>
              <div>
                <label className="text-xs font-medium text-muted-foreground">Maturity Date</label>
                <Input type="date" className="mt-1 bg-secondary border-border" value={form.maturity_date} onChange={(e) => setForm({ ...form, maturity_date: e.target.value })} />
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground">Nominee</label>
              <Input className="mt-1 bg-secondary border-border" placeholder="Nominee name" value={form.nominee} onChange={(e) => setForm({ ...form, nominee: e.target.value })} />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button
              onClick={handleSubmit}
              disabled={!form.provider || !form.policy_number || createMutation.isPending}
              className="bg-amber hover:bg-amber-dark text-navy font-semibold"
              size="sm"
            >
              {createMutation.isPending ? <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Adding...</> : "Add Policy"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
