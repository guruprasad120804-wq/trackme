"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
  Loader2,
  RefreshCw,
  CheckCircle2,
  LinkIcon,
  Trash2,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  getSubscription,
  getPlans,
  getEmailConfig,
  getMe,
  updateProfile,
  getWhatsAppConfig,
  saveWhatsAppConfig,
  uploadCAS,
  getImportHistory,
  triggerEmailScan,
  getEmailOAuthUrl,
  saveCASPassword,
  getAvailableBrokers,
  getBrokerConnections,
  getBrokerOAuthUrl,
  syncBrokerHoldings,
  disconnectBroker,
  saveBrokerCredentials,
} from "@/lib/api";

const TABS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "brokers", label: "Brokers", icon: LinkIcon },
  { id: "import", label: "Import Data", icon: Upload },
  { id: "email", label: "Email Scanning", icon: Mail },
  { id: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  { id: "subscription", label: "Subscription", icon: CreditCard },
];

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <SettingsContent />
    </Suspense>
  );
}

function SettingsContent() {
  const searchParams = useSearchParams();
  const initialTab = TABS.find(t => t.id === searchParams.get("tab"))?.id || "profile";
  const [tab, setTab] = useState(initialTab);
  const queryClient = useQueryClient();

  // --- Profile state ---
  const [profileName, setProfileName] = useState("");

  // --- CAS Upload state ---
  const casFileRef = useRef<HTMLInputElement>(null);
  const [casFile, setCasFile] = useState<File | null>(null);
  const [casPassword, setCasPassword] = useState("");
  const [casError, setCasError] = useState<string | null>(null);
  const [casResult, setCasResult] = useState<Record<string, unknown> | null>(null);

  // --- Email Scanning state ---
  const [emailCasPassword, setEmailCasPassword] = useState("");
  const [scanResult, setScanResult] = useState<Record<string, unknown> | null>(null);

  // --- WhatsApp state ---
  const [whatsappPhone, setWhatsappPhone] = useState("");

  // --- Queries ---
  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: () => getMe().then((r) => r.data),
    enabled: tab === "profile",
  });

  useEffect(() => {
    if (user?.name) setProfileName(user.name);
  }, [user]);

  const { data: subscription } = useQuery({
    queryKey: ["subscription"],
    queryFn: () => getSubscription().then((r) => r.data),
  });

  const { data: plans } = useQuery({
    queryKey: ["plans"],
    queryFn: () => getPlans().then((r) => r.data),
  });

  // --- Import History ---
  const { data: importHistory } = useQuery({
    queryKey: ["import-history"],
    queryFn: () => getImportHistory().then((r) => r.data),
    enabled: tab === "import",
  });

  // --- Email Config ---
  const { data: emailConfig } = useQuery({
    queryKey: ["email-config"],
    queryFn: () => getEmailConfig().then((r) => r.data),
    enabled: tab === "email",
  });

  const saveCASPasswordMutation = useMutation({
    mutationFn: () => saveCASPassword(emailCasPassword),
    onSuccess: () => {
      setEmailCasPassword("");
      queryClient.invalidateQueries({ queryKey: ["email-config"] });
    },
  });

  const scanNowMutation = useMutation({
    mutationFn: () => triggerEmailScan(),
    onSuccess: (res) => {
      setScanResult(res.data);
      queryClient.invalidateQueries({ queryKey: ["import-history"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["holdings-summary"] });
    },
  });

  // --- Profile Mutation ---
  const updateProfileMutation = useMutation({
    mutationFn: () => updateProfile({ name: profileName }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
      const stored = localStorage.getItem("trackme_user");
      if (stored) {
        const u = JSON.parse(stored);
        u.name = profileName;
        localStorage.setItem("trackme_user", JSON.stringify(u));
      }
    },
  });

  // --- WhatsApp ---
  const { data: waConfig } = useQuery({
    queryKey: ["whatsapp-config"],
    queryFn: () => getWhatsAppConfig().then((r) => r.data),
    enabled: tab === "whatsapp",
  });

  useEffect(() => {
    if (waConfig?.phone_number) setWhatsappPhone(waConfig.phone_number);
  }, [waConfig]);

  const saveWhatsAppMutation = useMutation({
    mutationFn: () => saveWhatsAppConfig({ phone_number: whatsappPhone }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["whatsapp-config"] });
    },
  });

  // --- Broker Connect ---
  const { data: availableBrokers } = useQuery({
    queryKey: ["available-brokers"],
    queryFn: () => getAvailableBrokers().then((r) => r.data),
    enabled: tab === "brokers",
  });

  const { data: brokerConnections, refetch: refetchBrokerConns } = useQuery({
    queryKey: ["broker-connections"],
    queryFn: () => getBrokerConnections().then((r) => r.data),
    enabled: tab === "brokers",
  });

  const [angelCreds, setAngelCreds] = useState({ client_code: "", pin: "", totp: "" });
  const [dhanToken, setDhanToken] = useState("");

  const syncBrokerMutation = useMutation({
    mutationFn: (connectionId: string) => syncBrokerHoldings(connectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["broker-connections"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["holdings-summary"] });
    },
  });

  const disconnectBrokerMutation = useMutation({
    mutationFn: (connectionId: string) => disconnectBroker(connectionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["broker-connections"] });
    },
  });

  const angelOneMutation = useMutation({
    mutationFn: () => saveBrokerCredentials("angel_one", angelCreds),
    onSuccess: () => {
      setAngelCreds({ client_code: "", pin: "", totp: "" });
      queryClient.invalidateQueries({ queryKey: ["broker-connections"] });
    },
  });

  const dhanMutation = useMutation({
    mutationFn: () => saveBrokerCredentials("dhan", { access_token: dhanToken }),
    onSuccess: () => {
      setDhanToken("");
      queryClient.invalidateQueries({ queryKey: ["broker-connections"] });
    },
  });

  const handleConnectBroker = async (brokerType: string) => {
    try {
      const res = await getBrokerOAuthUrl(brokerType);
      window.location.href = res.data.url;
    } catch {
      // OAuth URL fetch failed
    }
  };

  const handleConnectGmail = async () => {
    try {
      const res = await getEmailOAuthUrl();
      window.location.href = res.data.url;
    } catch {
      // OAuth URL fetch failed
    }
  };

  // --- CAS Upload Mutation ---
  const uploadCASMutation = useMutation({
    mutationFn: ({ file, password }: { file: File; password: string }) => uploadCAS(file, password),
    onSuccess: (res) => {
      setCasResult(res.data);
      setCasError(null);
      setCasFile(null);
      setCasPassword("");
      queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
      queryClient.invalidateQueries({ queryKey: ["holdings-summary"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["import-history"] });
    },
    onError: (err: any) => {
      setCasError(err.response?.data?.detail || "CAS upload failed");
    },
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
                      <Input
                        className="mt-1 bg-secondary border-border"
                        placeholder="Your name"
                        value={profileName}
                        onChange={(e) => setProfileName(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">Email</label>
                      <Input
                        className="mt-1 bg-secondary border-border"
                        disabled
                        value={user?.email || ""}
                      />
                      <p className="text-[10px] text-muted-foreground mt-1">Connected via Google OAuth</p>
                    </div>
                    <Button
                      className="bg-amber hover:bg-amber-dark text-navy font-semibold"
                      size="sm"
                      onClick={() => updateProfileMutation.mutate()}
                      disabled={updateProfileMutation.isPending || profileName === (user?.name || "")}
                    >
                      {updateProfileMutation.isPending ? (
                        <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Saving...</>
                      ) : (
                        "Save Changes"
                      )}
                    </Button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Brokers */}
            {tab === "brokers" && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                {/* Connected Brokers */}
                {brokerConnections && brokerConnections.length > 0 && (
                  <div className="rounded-xl border border-border bg-card p-6">
                    <h3 className="text-sm font-semibold text-foreground mb-4">Connected Brokers</h3>
                    <div className="space-y-3">
                      {brokerConnections.map((conn: any) => (
                        <div key={conn.id} className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-foreground">{conn.broker_name}</span>
                              <Badge variant="outline" className={cn(
                                "text-[10px]",
                                conn.status === "active" ? "border-emerald-500/30 text-emerald-400" : "border-red-500/30 text-red-400"
                              )}>
                                {conn.status}
                              </Badge>
                            </div>
                            <p className="text-[10px] text-muted-foreground mt-0.5">
                              {conn.last_synced ? `Last synced: ${new Date(conn.last_synced).toLocaleString()}` : "Never synced"}
                            </p>
                            {conn.sync_error && <p className="text-[10px] text-red-400">{conn.sync_error}</p>}
                          </div>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => syncBrokerMutation.mutate(conn.id)}
                              disabled={syncBrokerMutation.isPending}
                            >
                              {syncBrokerMutation.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                              onClick={() => disconnectBrokerMutation.mutate(conn.id)}
                              disabled={disconnectBrokerMutation.isPending}
                            >
                              <Trash2 className="h-3 w-3" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Available Brokers */}
                <div className="rounded-xl border border-border bg-card p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <LinkIcon className="h-5 w-5 text-amber" />
                    <h3 className="text-sm font-semibold text-foreground">Connect a Broker</h3>
                  </div>
                  <p className="text-xs text-muted-foreground mb-4">
                    Link your stock broker to automatically import holdings. Your credentials are encrypted and never stored as plain text.
                  </p>

                  {!availableBrokers || availableBrokers.length === 0 ? (
                    <div className="text-center py-8">
                      <LinkIcon className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
                      <p className="text-sm text-muted-foreground">No brokers configured yet</p>
                      <p className="text-xs text-muted-foreground mt-1">Broker API credentials need to be set up by the admin</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {availableBrokers.map((broker: any) => {
                        const isConnected = brokerConnections?.some((c: any) => c.broker_type === broker.type);
                        return (
                          <div
                            key={broker.type}
                            className={cn(
                              "rounded-lg border p-4 transition-colors",
                              isConnected ? "border-emerald-500/30 bg-emerald-500/5" : "border-border hover:border-amber/30"
                            )}
                          >
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="text-sm font-medium text-foreground">{broker.name}</p>
                                <p className="text-[10px] text-muted-foreground mt-0.5">
                                  {broker.type === "angel_one" ? "API Key + TOTP" : broker.type === "dhan" ? "Access Token" : "OAuth Connect"}
                                </p>
                              </div>
                              {isConnected ? (
                                <Badge className="bg-emerald-500/15 text-emerald-400 border-none text-[10px]">Connected</Badge>
                              ) : broker.auth_type === "credentials_form" ? null : (
                                <Button
                                  size="sm"
                                  className="bg-amber hover:bg-amber-dark text-navy font-semibold"
                                  onClick={() => handleConnectBroker(broker.type)}
                                >
                                  Connect
                                </Button>
                              )}
                            </div>

                            {/* Angel One credentials form */}
                            {broker.type === "angel_one" && broker.auth_type === "credentials_form" && !isConnected && (
                              <div className="mt-3 space-y-2">
                                <Input
                                  className="bg-secondary border-border text-xs"
                                  placeholder="Client Code"
                                  value={angelCreds.client_code}
                                  onChange={(e) => setAngelCreds(p => ({ ...p, client_code: e.target.value }))}
                                />
                                <Input
                                  className="bg-secondary border-border text-xs"
                                  type="password"
                                  placeholder="PIN"
                                  value={angelCreds.pin}
                                  onChange={(e) => setAngelCreds(p => ({ ...p, pin: e.target.value }))}
                                />
                                <Input
                                  className="bg-secondary border-border text-xs"
                                  placeholder="TOTP (from authenticator app)"
                                  value={angelCreds.totp}
                                  onChange={(e) => setAngelCreds(p => ({ ...p, totp: e.target.value }))}
                                />
                                <Button
                                  size="sm"
                                  className="bg-amber hover:bg-amber-dark text-navy font-semibold w-full"
                                  onClick={() => angelOneMutation.mutate()}
                                  disabled={!angelCreds.client_code || !angelCreds.pin || !angelCreds.totp || angelOneMutation.isPending}
                                >
                                  {angelOneMutation.isPending ? (
                                    <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Connecting...</>
                                  ) : (
                                    "Connect"
                                  )}
                                </Button>
                              </div>
                            )}

                            {/* Dhan access token form */}
                            {broker.type === "dhan" && broker.auth_type === "credentials_form" && !isConnected && (
                              <div className="mt-3 space-y-2">
                                <p className="text-[10px] text-muted-foreground">
                                  Generate an access token from <a href="https://web.dhan.co" target="_blank" rel="noopener noreferrer" className="text-amber hover:underline">web.dhan.co</a> and paste it below
                                </p>
                                <Input
                                  className="bg-secondary border-border text-xs"
                                  type="password"
                                  placeholder="Paste your Dhan access token"
                                  value={dhanToken}
                                  onChange={(e) => setDhanToken(e.target.value)}
                                />
                                <Button
                                  size="sm"
                                  className="bg-amber hover:bg-amber-dark text-navy font-semibold w-full"
                                  onClick={() => dhanMutation.mutate()}
                                  disabled={!dhanToken || dhanMutation.isPending}
                                >
                                  {dhanMutation.isPending ? (
                                    <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Connecting...</>
                                  ) : (
                                    "Connect"
                                  )}
                                </Button>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </motion.div>
            )}

            {/* Import Data */}
            {tab === "import" && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                {/* --- CAS Upload (Primary) --- */}
                <div className="rounded-xl border border-border bg-card p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <Upload className="h-5 w-5 text-amber" />
                    <h3 className="text-sm font-semibold text-foreground">Import CAS Statement</h3>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    Upload your CAMS/KFintech Consolidated Account Statement (PDF) to import all mutual fund holdings and transactions.
                  </p>

                  <div className="bg-secondary/30 rounded-lg p-3 mb-4 text-xs text-muted-foreground space-y-1">
                    <p className="font-medium text-foreground">Where to get your CAS:</p>
                    <p>1. Visit <a href="https://mycams.camsonline.com" target="_blank" rel="noopener noreferrer" className="text-amber hover:underline">mycams.camsonline.com</a> (CAMS)</p>
                    <p>2. Or <a href="https://mfs.kfintech.com" target="_blank" rel="noopener noreferrer" className="text-amber hover:underline">mfs.kfintech.com</a> (KFintech)</p>
                    <p>3. Request a &ldquo;Consolidated Account Statement&rdquo; with transaction details</p>
                  </div>

                  <input
                    type="file"
                    accept=".pdf"
                    ref={casFileRef}
                    className="hidden"
                    onChange={(e) => { setCasFile(e.target.files?.[0] || null); setCasError(null); setCasResult(null); }}
                  />
                  <div
                    className="border-2 border-dashed border-border rounded-xl p-8 text-center hover:border-amber/30 transition-colors cursor-pointer"
                    onClick={() => casFileRef.current?.click()}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={(e) => {
                      e.preventDefault();
                      const file = e.dataTransfer.files[0];
                      if (file?.type === "application/pdf") { setCasFile(file); setCasError(null); setCasResult(null); }
                    }}
                  >
                    <Upload className="h-8 w-8 text-muted-foreground/50 mx-auto mb-3" />
                    {casFile ? (
                      <>
                        <p className="text-sm text-amber font-medium">{casFile.name}</p>
                        <p className="text-xs text-muted-foreground mt-1">{(casFile.size / 1024).toFixed(0)} KB</p>
                      </>
                    ) : (
                      <>
                        <p className="text-sm text-muted-foreground">Drop your CAS PDF here</p>
                        <p className="text-xs text-muted-foreground mt-1">or click to browse</p>
                      </>
                    )}
                  </div>
                  <div className="mt-4">
                    <label className="text-xs font-medium text-muted-foreground">CAS Password</label>
                    <Input
                      type="password"
                      className="mt-1 bg-secondary border-border"
                      placeholder="Usually DOB in DDMMYYYY format (e.g., 15081990)"
                      value={casPassword}
                      onChange={(e) => setCasPassword(e.target.value)}
                    />
                  </div>
                  {casError && <p className="text-xs text-red-400 mt-2">{casError}</p>}
                  {casResult && (
                    <div className="bg-secondary/50 rounded-lg p-3 mt-3 text-xs text-muted-foreground space-y-1">
                      {casResult.status === "failed" ? (
                        <>
                          <p className="text-red-400 font-medium">Import failed</p>
                          <p>{String(casResult.error || "")}</p>
                        </>
                      ) : (
                        <>
                          <p className="text-emerald-400 font-medium">Import successful!</p>
                          <p>Schemes added: <span className="text-foreground font-medium">{Number(casResult.schemes_added ?? 0)}</span></p>
                          <p>Transactions added: <span className="text-foreground font-medium">{Number(casResult.transactions_added ?? 0)}</span></p>
                          <p>Folios added: <span className="text-foreground font-medium">{Number(casResult.folios_added ?? 0)}</span></p>
                          <p>Holdings updated: <span className="text-foreground font-medium">{Number(casResult.holdings_updated ?? 0)}</span></p>
                          {Array.isArray(casResult.errors) && casResult.errors.length > 0 && (
                            <p className="text-yellow-400">Warnings: {casResult.errors.length}</p>
                          )}
                        </>
                      )}
                    </div>
                  )}
                  <Button
                    className="mt-4 bg-amber hover:bg-amber-dark text-navy font-semibold"
                    size="sm"
                    disabled={!casFile || !casPassword || uploadCASMutation.isPending}
                    onClick={() => { if (casFile) uploadCASMutation.mutate({ file: casFile, password: casPassword }); }}
                  >
                    {uploadCASMutation.isPending ? (
                      <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Uploading...</>
                    ) : (
                      "Upload & Import"
                    )}
                  </Button>
                </div>

                {/* --- Import History --- */}
                <div className="rounded-xl border border-border bg-card p-6">
                  <h3 className="text-sm font-semibold text-foreground mb-4">Import History</h3>
                  {(!importHistory || importHistory.length === 0) && (
                    <p className="text-xs text-muted-foreground">No imports yet</p>
                  )}
                  <div className="space-y-2">
                    {(importHistory || []).map((log: any) => (
                      <div key={log.id} className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg">
                        <div>
                          <p className="text-xs font-medium text-foreground">{log.file_name || log.source}</p>
                          <p className="text-[10px] text-muted-foreground">
                            {new Date(log.created_at).toLocaleString()} &middot; {log.schemes_added} schemes, {log.transactions_added} txns
                          </p>
                        </div>
                        <Badge variant="outline" className={cn(
                          "text-[10px]",
                          log.status === "completed" ? "border-emerald-500/30 text-emerald-400" : "border-red-500/30 text-red-400"
                        )}>
                          {log.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>

                {/* --- Manual Entry placeholder --- */}
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
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                <div className="rounded-xl border border-border bg-card p-6">
                  <div className="flex items-center gap-3 mb-2">
                    <Mail className="h-5 w-5 text-amber" />
                    <h3 className="text-sm font-semibold text-foreground">Gmail Integration</h3>
                  </div>
                  <p className="text-xs text-muted-foreground mb-4">
                    Connect your Gmail to automatically detect and import CAS statements sent by CAMS, KFintech, and MFCentral.
                  </p>

                  {emailConfig?.configured ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-emerald-400 text-sm">
                        <CheckCircle2 className="h-4 w-4" />
                        <span className="font-medium">Connected</span>
                        <span className="text-muted-foreground text-xs ml-2">{emailConfig.email_address}</span>
                      </div>
                      {emailConfig.last_scanned && (
                        <p className="text-xs text-muted-foreground">
                          Last scanned: {new Date(emailConfig.last_scanned).toLocaleString()}
                        </p>
                      )}

                      {/* CAS Password */}
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">
                          CAS Password {emailConfig.has_cas_password && <span className="text-emerald-400">(saved)</span>}
                        </label>
                        <p className="text-[10px] text-muted-foreground mt-0.5 mb-1">
                          The password to open your CAS PDFs — needed to parse email attachments
                        </p>
                        <div className="flex gap-2">
                          <Input
                            type="password"
                            className="bg-secondary border-border"
                            placeholder="Usually DOB in DDMMYYYY format"
                            value={emailCasPassword}
                            onChange={(e) => setEmailCasPassword(e.target.value)}
                          />
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => saveCASPasswordMutation.mutate()}
                            disabled={!emailCasPassword || saveCASPasswordMutation.isPending}
                          >
                            {saveCASPasswordMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save"}
                          </Button>
                        </div>
                      </div>

                      {/* Scan Now */}
                      <Button
                        className="bg-amber hover:bg-amber-dark text-navy font-semibold"
                        size="sm"
                        disabled={scanNowMutation.isPending || !emailConfig.has_cas_password}
                        onClick={() => scanNowMutation.mutate()}
                      >
                        {scanNowMutation.isPending ? (
                          <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Scanning...</>
                        ) : (
                          <><RefreshCw className="h-4 w-4 mr-1" />Scan Now</>
                        )}
                      </Button>
                      {!emailConfig.has_cas_password && (
                        <p className="text-[10px] text-yellow-400">Save your CAS password above before scanning</p>
                      )}

                      {/* Scan results */}
                      {scanResult && (
                        <div className="bg-secondary/50 rounded-lg p-3 text-xs text-muted-foreground space-y-1">
                          <p className="text-emerald-400 font-medium">Scan complete</p>
                          <p>Emails found: <span className="text-foreground font-medium">{scanResult.emails_found as number ?? 0}</span></p>
                          <p>Processed: <span className="text-foreground font-medium">{scanResult.processed as number ?? 0}</span></p>
                          <p>Imported: <span className="text-foreground font-medium">{scanResult.imported as number ?? 0}</span></p>
                          {(scanResult.errors as string[])?.length > 0 && (
                            <p className="text-yellow-400">Errors: {(scanResult.errors as string[]).length}</p>
                          )}
                          {scanResult.status === "skipped" && (
                            <p className="text-yellow-400">{scanResult.reason as string}</p>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="bg-secondary/30 rounded-lg p-3 text-xs text-muted-foreground space-y-1">
                        <p className="font-medium text-foreground">How it works:</p>
                        <p>1. Connect your Gmail (read-only access to find CAS emails)</p>
                        <p>2. Save your CAS password (encrypted, used to open CAS PDFs)</p>
                        <p>3. Click &ldquo;Scan Now&rdquo; or let auto-scan find new CAS emails</p>
                      </div>
                      <Button
                        className="bg-amber hover:bg-amber-dark text-navy font-semibold"
                        size="sm"
                        onClick={handleConnectGmail}
                      >
                        <Shield className="h-4 w-4 mr-2" />
                        Connect Gmail
                      </Button>
                    </div>
                  )}
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

                  {waConfig?.configured ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-emerald-400 text-sm">
                        <CheckCircle2 className="h-4 w-4" />
                        <span className="font-medium">Connected</span>
                        <span className="text-muted-foreground text-xs ml-2">{waConfig.phone_number}</span>
                      </div>
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Update Phone Number</label>
                        <Input
                          className="mt-1 bg-secondary border-border"
                          placeholder="+91 9876543210"
                          value={whatsappPhone}
                          onChange={(e) => setWhatsappPhone(e.target.value)}
                        />
                      </div>
                      <Button
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                        size="sm"
                        onClick={() => saveWhatsAppMutation.mutate()}
                        disabled={!whatsappPhone || saveWhatsAppMutation.isPending || whatsappPhone === waConfig.phone_number}
                      >
                        {saveWhatsAppMutation.isPending ? (
                          <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Saving...</>
                        ) : (
                          "Update"
                        )}
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div>
                        <label className="text-xs font-medium text-muted-foreground">Phone Number</label>
                        <Input
                          className="mt-1 bg-secondary border-border"
                          placeholder="+91 9876543210"
                          value={whatsappPhone}
                          onChange={(e) => setWhatsappPhone(e.target.value)}
                        />
                      </div>
                      <Button
                        className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                        size="sm"
                        onClick={() => saveWhatsAppMutation.mutate()}
                        disabled={!whatsappPhone || saveWhatsAppMutation.isPending}
                      >
                        {saveWhatsAppMutation.isPending ? (
                          <><Loader2 className="h-4 w-4 mr-1 animate-spin" />Linking...</>
                        ) : (
                          "Link WhatsApp"
                        )}
                      </Button>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
