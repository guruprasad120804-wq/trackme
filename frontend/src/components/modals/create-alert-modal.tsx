"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createAlert } from "@/lib/api";

const CONDITIONS = [
  { value: "PRICE_ABOVE", label: "Price Above" },
  { value: "PRICE_BELOW", label: "Price Below" },
  { value: "PORTFOLIO_VALUE_ABOVE", label: "Portfolio Value Above" },
  { value: "PORTFOLIO_VALUE_BELOW", label: "Portfolio Value Below" },
  { value: "DAY_CHANGE_PCT", label: "Day Change %" },
  { value: "SIP_REMINDER", label: "SIP Reminder" },
];

const CHANNELS = [
  { value: "PUSH", label: "In-App" },
  { value: "EMAIL", label: "Email" },
  { value: "WHATSAPP", label: "WhatsApp" },
];

interface CreateAlertModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CreateAlertModal({ open, onOpenChange }: CreateAlertModalProps) {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [condition, setCondition] = useState("PRICE_ABOVE");
  const [assetName, setAssetName] = useState("");
  const [threshold, setThreshold] = useState("");
  const [channels, setChannels] = useState<string[]>(["PUSH"]);
  const [isRecurring, setIsRecurring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isPriceCondition = condition.startsWith("PRICE_");

  const mutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => createAlert(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      onOpenChange(false);
      resetForm();
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || "Failed to create alert");
    },
  });

  const resetForm = () => {
    setName("");
    setCondition("PRICE_ABOVE");
    setAssetName("");
    setThreshold("");
    setChannels(["PUSH"]);
    setIsRecurring(false);
    setError(null);
  };

  const handleSubmit = () => {
    if (!name.trim()) { setError("Name is required"); return; }
    if (!threshold) { setError("Threshold is required"); return; }
    setError(null);

    mutation.mutate({
      name: name.trim(),
      condition,
      asset_name: isPriceCondition ? assetName : undefined,
      threshold: parseFloat(threshold),
      channels,
      is_recurring: isRecurring,
    });
  };

  const toggleChannel = (ch: string) => {
    setChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md bg-card border-border">
        <DialogHeader>
          <DialogTitle className="text-foreground">Create Alert</DialogTitle>
          <DialogDescription>
            Get notified when conditions are met
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Name */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Alert Name</label>
            <Input
              className="mt-1 bg-secondary border-border"
              placeholder="e.g., Reliance above 3000"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Condition */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">Condition</label>
            <select
              className="mt-1 w-full rounded-lg border border-border bg-secondary px-3 py-2 text-sm text-foreground"
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
            >
              {CONDITIONS.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </select>
          </div>

          {/* Asset (for price conditions) */}
          {isPriceCondition && (
            <div>
              <label className="text-xs font-medium text-muted-foreground">Asset Name / Symbol</label>
              <Input
                className="mt-1 bg-secondary border-border"
                placeholder="e.g., RELIANCE or HDFC Flexi Cap"
                value={assetName}
                onChange={(e) => setAssetName(e.target.value)}
              />
            </div>
          )}

          {/* Threshold */}
          <div>
            <label className="text-xs font-medium text-muted-foreground">
              {condition === "DAY_CHANGE_PCT" ? "Change %" : "Target Value (₹)"}
            </label>
            <Input
              type="number"
              className="mt-1 bg-secondary border-border"
              placeholder={condition === "DAY_CHANGE_PCT" ? "e.g., 5" : "e.g., 3000"}
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
            />
          </div>

          {/* Channels */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-2 block">Notify via</label>
            <div className="flex gap-2">
              {CHANNELS.map((ch) => (
                <button
                  key={ch.value}
                  type="button"
                  onClick={() => toggleChannel(ch.value)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                    channels.includes(ch.value)
                      ? "bg-amber/15 text-amber border-amber/30"
                      : "bg-secondary text-muted-foreground border-border hover:border-amber/20"
                  }`}
                >
                  {ch.label}
                </button>
              ))}
            </div>
          </div>

          {/* Recurring */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isRecurring}
              onChange={(e) => setIsRecurring(e.target.checked)}
              className="rounded border-border"
            />
            <span className="text-xs text-muted-foreground">Recurring (trigger multiple times)</span>
          </label>

          {error && <p className="text-xs text-red-400">{error}</p>}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={() => { onOpenChange(false); resetForm(); }}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="bg-amber hover:bg-amber-dark text-navy font-semibold"
            size="sm"
          >
            {mutation.isPending ? (
              <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Creating...</>
            ) : (
              "Create Alert"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
