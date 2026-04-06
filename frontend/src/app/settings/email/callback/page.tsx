"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { saveEmailOAuthCallback } from "@/lib/api";
import { Loader2 } from "lucide-react";

function EmailCallbackHandler() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("No authorization code received");
      return;
    }

    const redirectUri = `${window.location.origin}/settings/email/callback`;

    saveEmailOAuthCallback(code, redirectUri)
      .then(() => {
        router.push("/settings?tab=email&connected=true");
      })
      .catch((err) => {
        setError(err.response?.data?.detail || "Gmail connection failed. Please try again.");
      });
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="text-center">
        <p className="text-red-400 text-sm mb-4">{error}</p>
        <a href="/settings?tab=email" className="text-amber hover:underline text-sm">
          Back to settings
        </a>
      </div>
    );
  }

  return (
    <div className="text-center">
      <Loader2 className="h-8 w-8 animate-spin text-amber mx-auto mb-4" />
      <p className="text-sm text-muted-foreground">Connecting Gmail...</p>
    </div>
  );
}

export default function EmailCallbackPage() {
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
        <EmailCallbackHandler />
      </Suspense>
    </div>
  );
}
