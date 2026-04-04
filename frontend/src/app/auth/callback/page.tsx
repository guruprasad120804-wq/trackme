"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { authGoogle } from "@/lib/api";
import { Loader2 } from "lucide-react";

export default function AuthCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    if (!code) {
      setError("No authorization code received");
      return;
    }

    const redirectUri = `${window.location.origin}/auth/callback`;

    authGoogle(code, redirectUri)
      .then((res) => {
        const { access_token, refresh_token, user } = res.data;
        localStorage.setItem("trackme_token", access_token);
        localStorage.setItem("trackme_refresh_token", refresh_token);
        localStorage.setItem("trackme_user", JSON.stringify(user));
        router.push("/dashboard");
      })
      .catch((err) => {
        console.error("Auth failed:", err);
        setError(err.response?.data?.detail || "Authentication failed. Please try again.");
      });
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <p className="text-red-400 text-sm mb-4">{error}</p>
          <a href="/login" className="text-amber hover:underline text-sm">
            Back to login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <Loader2 className="h-8 w-8 animate-spin text-amber mx-auto mb-4" />
        <p className="text-sm text-muted-foreground">Signing you in...</p>
      </div>
    </div>
  );
}
