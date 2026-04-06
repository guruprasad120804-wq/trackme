"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { saveBrokerOAuthCallback } from "@/lib/api";
import { Loader2 } from "lucide-react";

function BrokerCallbackHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("auth_code") || searchParams.get("request_token") || searchParams.get("code");
    const state = searchParams.get("state") || searchParams.get("broker");
    if (!code || !state) {
      setError("Missing authorization code or broker type");
      return;
    }

    const redirectUri = `${window.location.origin}/settings/brokers/callback`;

    saveBrokerOAuthCallback(state, code, redirectUri)
      .then(() => {
        router.push(`/settings?tab=brokers&connected=${state}`);
      })
      .catch((err) => {
        setError(err.response?.data?.detail || "Broker connection failed. Please try again.");
      });
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="text-center">
        <p className="text-red-400 text-sm mb-4">{error}</p>
        <a href="/settings?tab=brokers" className="text-amber hover:underline text-sm">
          Back to settings
        </a>
      </div>
    );
  }

  return (
    <div className="text-center">
      <Loader2 className="h-8 w-8 animate-spin text-amber mx-auto mb-4" />
      <p className="text-sm text-muted-foreground">Connecting broker...</p>
    </div>
  );
}

export default function BrokerCallbackPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Suspense
        fallback={
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin text-amber mx-auto mb-4" />
            <p className="text-sm text-muted-foreground">Loading...</p>
          </div>
        }
      >
        <BrokerCallbackHandler />
      </Suspense>
    </div>
  );
}
