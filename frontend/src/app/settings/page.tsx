"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  User,
  Mail,
  MessageCircle,
  CreditCard,
  Upload,
  Shield,
  Crown,
  Check,
  Zap,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { getSubscription, getPlans, getEmailConfig, getWhatsAppConfig } from "@/lib/api";

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "import", label: "Import Data", icon: Upload },
  { id: "email", label: "Email Scanning", icon: Mail },
  { id: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  { id: "subscription", label: "Subscription", icon: CreditCard },
];

export default function SettingsPage() {
  const [tab, setTab] = useState("profile");

  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => getSubscription().then((r) => r.data),
  });

  const { data: plans } = useQuery({
    queryKey: ["plans"],
    queryFn: () => getPlans().then((r) => r.data),
  });

  return (
    <div className="min-h-screen">
      <Header title="Settings" subtitle="Manage your account and preferences" />

      <div className="p-6">
        <div className="flex gap-6">
          {/* Settings nav */}
          <div className="w-56 shrink-0 space-y-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  "flex items-center gap-3 w-full px-3 py-2.5 text-sm font-medium rounded-lg transition-colors",
                  tab === t.id
                    ? "bg-amber/15 text-amber"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
              >
                <t.icon className="h-4 w-4" />
                {t.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 max-w-2xl">
            {/* Profile */}
            {tab === "profile" && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div className="rounded-xl border border-border bg-card p-6">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Profile</h3>
                  <div className="space-y-4">
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">Name</label>
                      <Input className="mt-1 bg-secondary border-border" placeholder="Your name" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">Email</label>
                      <Input className="mt-1 bg-secondary border-border" disabled placeholder="email@gmail.com" />
                      <p className="text-[10px] text-muted-foreground mt-1">Connected via Google OAuth</p>
                    </div>
                    <Button className="bg-amber hover:bg-amber-dark text-navy font-semibold" size="sm">
                      Save Changes
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Import Data */}
            {tab === "import" && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div className="rounded-xl border border-border bg-card p-6">
                  <h3 className="text-sm font-semibold text-foreground mb-2">Import CAS Statement</h3>
                  <p className="text-xs text-muted-foreground mb-4">
                    Upload your CAMS/KFintech Consolidated Account Statement (PDF)
                  </p>
                  <div className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-amber/30 transition-colors">
                    <Upload className="h-8 w-8 text-muted-foreground/50 mx-auto mb-3" />
                    <p className="text-sm text-muted-foreground">Drop your CAS PDF here</p>
                    <p className="text-xs text-muted-foreground mt-1">or click to browse</p>
                  </div>
                  <div className="mt-4">
                    <label className="text-xs font-medium text-muted-foreground">CAS Password</label>
                    <Input type="password" className="mt-1 bg-secondary border-border" placeholder="Enter CAS password" />
                  </div>
                  <Button className="mt-4 bg-amber hover:bg-amber-dark text-navy font-semibold" size="sm">
                    Upload & Import
                  </Button>
                </div>

                <div className="rounded-xl border border-border bg-card p-6">
                  <h3 className="text-sm font-semibold text-foreground mb-2">Manual Entry</h3>
                  <p className="text-xs text-muted-foreground mb-4">
                    Manually add a transaction for any asset type
                  </p>
                  <Button variant="outline" size="sm">
                    Add Transaction
                  </Button>
                </div>
              </motion.div>
            )}

            {/* Subscription */}
            {tab === "subscription" && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                {/* Current plan */}
                <div className="rounded-xl border border-border bg-card p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber/10">
                        <Crown className="h-5 w-5 text-amber" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-foreground capitalize">
                          {subscription?.plan || "Free"} Plan
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {subscription?.status === "active" ? "Active" : "Inactive"}
                        </p>
                      </div>
                    </div>
                    <Badge className="bg-amber/15 text-amber border-none capitalize">
                      {subscription?.plan || "free"}
                    </Badge>
                  </div>
                </div>

                {/* Plan cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {(plans || []).map((plan: any) => (
                    <div
                      key={plan.name}
                      className={cn(
                        "rounded-xl border bg-card p-6 card-hover",
                        plan.name === "Premium" ? "border-amber" : "border-border"
                      )}
                    >
                      {plan.name === "Premium" && (
                        <Badge className="bg-amber text-navy text-[10px] font-bold mb-3">
                          Most Popular
                        </Badge>
                      )}
                      <h3 className="text-lg font-bold text-foreground">{plan.name}</h3>
                      <div className="mt-2">
                        <span className="text-2xl font-bold text-foreground">
                          ₹{plan.price_monthly}
                        </span>
                        <span className="text-xs text-muted-foreground">/month</span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">
                        or ₹{plan.price_yearly}/year (save {Math.round((1 - plan.price_yearly / (plan.price_monthly * 12)) * 100)}%)
                      </p>

                      <ul className="mt-4 space-y-2">
                        {plan.features.map((f: string) => (
                          <li key={f} className="flex items-center gap-2 text-xs text-muted-foreground">
                            <Check className="h-3.5 w-3.5 text-amber shrink-0" />
                            {f}
                          </li>
                        ))}
                      </ul>

                      <Button
                        className={cn(
                          "w-full mt-5 font-semibold",
                          plan.name === "Premium"
                            ? "bg-amber hover:bg-amber-dark text-navy"
                            : "bg-secondary hover:bg-secondary/80 text-foreground"
                        )}
                        size="sm"
                      >
                        {subscription?.plan === plan.name.toLowerCase()
                          ? "Current Plan"
                          : `Upgrade to ${plan.name}`}
                      </Button>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {/* Email Scanning */}
            {tab === "email" && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="rounded-xl border border-border bg-card p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <Mail className="h-5 w-5 text-amber" />
                    <h3 className="text-sm font-semibold text-foreground">Gmail Integration</h3>
                  </div>
                  <p className="text-xs text-muted-foreground mb-4">
                    Connect your Gmail to automatically detect and import CAS statements sent by CAMS and KFintech.
                  </p>
                  <Button className="bg-amber hover:bg-amber-dark text-navy font-semibold" size="sm">
                    <Shield className="h-4 w-4 mr-2" />
                    Connect Gmail
                  </Button>
                </div>
              </motion.div>
            )}

            {/* WhatsApp */}
            {tab === "whatsapp" && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="rounded-xl border border-border bg-card p-6">
                  <div className="flex items-center gap-3 mb-4">
                    <MessageCircle className="h-5 w-5 text-emerald-400" />
                    <h3 className="text-sm font-semibold text-foreground">WhatsApp Bot</h3>
                  </div>
                  <p className="text-xs text-muted-foreground mb-4">
                    Link your WhatsApp to get portfolio updates, alerts, and ask questions on the go.
                  </p>
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">Phone Number</label>
                      <Input className="mt-1 bg-secondary border-border" placeholder="+91 9876543210" />
                    </div>
                    <Button className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold" size="sm">
                      Link WhatsApp
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
