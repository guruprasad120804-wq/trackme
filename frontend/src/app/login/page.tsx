"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { TrendingUp, ArrowRight, Shield, Zap, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";

const features = [
  {
    icon: BarChart3,
    title: "Smart Portfolio Tracking",
    desc: "Track stocks, mutual funds, ETFs across all brokers in one place",
  },
  {
    icon: Zap,
    title: "AI-Powered Insights",
    desc: "Get intelligent analysis and answers about your investments",
  },
  {
    icon: Shield,
    title: "Bank-Grade Security",
    desc: "Your financial data is encrypted and never shared",
  },
];

export default function LoginPage() {
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = () => {
    setLoading(true);
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    const redirectUri = `${window.location.origin}/auth/callback`;
    const scope = "openid email profile";
    const url = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}&access_type=offline&prompt=consent`;
    window.location.href = url;
  };

  return (
    <div className="flex min-h-screen">
      {/* Left — Branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between bg-gradient-to-br from-navy via-navy-light to-navy-lighter p-12 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-20 left-10 h-96 w-96 rounded-full bg-amber blur-3xl" />
          <div className="absolute bottom-20 right-10 h-64 w-64 rounded-full bg-amber blur-3xl" />
        </div>

        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber text-navy">
              <TrendingUp className="h-6 w-6" />
            </div>
            <span className="text-2xl font-bold text-foreground">TrackMe</span>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-4xl font-bold leading-tight text-foreground mb-4">
              Your investments,
              <br />
              <span className="text-amber">intelligently tracked.</span>
            </h1>
            <p className="text-lg text-muted-foreground max-w-md">
              The most powerful portfolio tracker for Indian investors. AI-powered insights, real-time alerts, all brokers in one place.
            </p>
          </motion.div>
        </div>

        <div className="relative z-10 space-y-6">
          {features.map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5, delay: 0.2 + i * 0.15 }}
              className="flex items-start gap-4"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber/10 border border-amber/20">
                <f.icon className="h-5 w-5 text-amber" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-foreground">{f.title}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">{f.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right — Login */}
      <div className="flex flex-1 items-center justify-center p-8 bg-background">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-sm"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-3 mb-10 justify-center">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber text-navy">
              <TrendingUp className="h-6 w-6" />
            </div>
            <span className="text-2xl font-bold text-foreground">TrackMe</span>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-foreground">Welcome back</h2>
            <p className="text-sm text-muted-foreground mt-2">
              Sign in to access your portfolio
            </p>
          </div>

          <Button
            onClick={handleGoogleLogin}
            disabled={loading}
            size="lg"
            className="w-full bg-white hover:bg-gray-100 text-gray-900 font-semibold border border-gray-300 h-12"
          >
            <svg className="h-5 w-5 mr-3" viewBox="0 0 24 24">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            {loading ? "Redirecting..." : "Continue with Google"}
          </Button>

          <p className="text-center text-xs text-muted-foreground mt-6">
            By continuing, you agree to our{" "}
            <a href="#" className="text-amber hover:underline">Terms</a> and{" "}
            <a href="#" className="text-amber hover:underline">Privacy Policy</a>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
