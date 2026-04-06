"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Briefcase,
  ArrowLeftRight,
  Bell,
  MessageCircle,
  Settings,
  Upload,
  CreditCard,
  LogOut,
  TrendingUp,
  Shield,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/transactions", label: "Transactions", icon: ArrowLeftRight },
  { href: "/alerts", label: "Alerts", icon: Bell },
  { href: "/insurance", label: "Insurance", icon: Shield },
  { href: "/chat", label: "AI Assistant", icon: MessageCircle },
  { href: "/settings", label: "Settings", icon: Settings },
];

const secondaryItems = [
  { href: "/settings?tab=import", label: "Import Data", icon: Upload },
  { href: "/settings?tab=subscription", label: "Subscription", icon: CreditCard },
];

export function Sidebar() {
  const pathname = usePathname();

  const handleLogout = () => {
    localStorage.removeItem("trackme_token");
    localStorage.removeItem("trackme_refresh_token");
    window.location.href = "/login";
  };

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-64 flex-col border-r border-border bg-sidebar">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-6 border-b border-border">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber text-navy font-bold text-lg">
          <TrendingUp className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-foreground">TrackMe</h1>
          <p className="text-[10px] text-muted-foreground -mt-1">Portfolio Intelligence</p>
        </div>
      </div>

      {/* Primary Nav */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                isActive
                  ? "bg-amber/15 text-amber"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-4.5 w-4.5", isActive && "text-amber")} />
              {item.label}
            </Link>
          );
        })}

        <div className="my-4 border-t border-border" />

        {secondaryItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-secondary hover:text-foreground transition-all"
          >
            <item.icon className="h-4.5 w-4.5" />
            {item.label}
          </Link>
        ))}
      </nav>

      {/* User / Logout */}
      <div className="border-t border-border p-3">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-red-500/10 hover:text-red-400 transition-all"
        >
          <LogOut className="h-4.5 w-4.5" />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
