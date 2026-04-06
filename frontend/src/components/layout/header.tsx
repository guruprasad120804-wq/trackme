"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Search, Plus, Check } from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { getUnreadCount, getNotifications, markAllNotificationsRead, markNotificationRead } from "@/lib/api";

interface HeaderProps {
  title: string;
  subtitle?: string;
  user?: { name: string; email: string; avatar_url?: string };
}

export function Header({ title, subtitle, user }: HeaderProps) {
  const queryClient = useQueryClient();
  const [showNotifs, setShowNotifs] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: unreadData } = useQuery({
    queryKey: ["unread-count"],
    queryFn: () => getUnreadCount().then((r) => r.data),
    refetchInterval: 30000,
  });

  const { data: notifications, isLoading: notifsLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => getNotifications().then((r) => r.data),
    enabled: showNotifs,
  });

  const markAllRead = useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unread-count"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markRead = useMutation({
    mutationFn: (id: string) => markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["unread-count"] });
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const count = unreadData?.count || 0;

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowNotifs(false);
      }
    };
    if (showNotifs) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showNotifs]);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/80 backdrop-blur-xl px-6">
      <div>
        <h2 className="text-xl font-bold text-foreground">{title}</h2>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Search */}
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search assets, transactions..."
            className="w-64 pl-9 bg-secondary border-border text-sm"
          />
        </div>

        {/* Quick Add */}
        <Button size="sm" className="bg-amber hover:bg-amber-dark text-navy font-semibold">
          <Plus className="h-4 w-4 mr-1" />
          Add
        </Button>

        {/* Notifications */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className="relative rounded-lg p-2 text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          >
            <Bell className="h-5 w-5" />
            {count > 0 && (
              <span className="absolute -top-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-amber text-[9px] font-bold text-navy">
                {count > 9 ? "9+" : count}
              </span>
            )}
          </button>

          {/* Dropdown */}
          {showNotifs && (
            <div className="absolute right-0 top-full mt-2 w-80 rounded-xl border border-border bg-card shadow-xl z-50">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <span className="text-sm font-semibold text-foreground">Notifications</span>
                {count > 0 && (
                  <button
                    onClick={() => markAllRead.mutate()}
                    className="text-xs text-amber hover:underline"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-72 overflow-y-auto divide-y divide-border">
                {notifsLoading ? (
                  <div className="p-3 space-y-3">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="flex gap-2 px-1">
                        <Skeleton className="h-2 w-2 rounded-full mt-1.5 shrink-0" />
                        <div className="flex-1"><Skeleton className="h-3 w-32 mb-1.5" /><Skeleton className="h-2.5 w-full" /><Skeleton className="h-2 w-20 mt-1" /></div>
                      </div>
                    ))}
                  </div>
                ) : (notifications || []).length === 0 ? (
                  <div className="p-6 text-center">
                    <Bell className="h-6 w-6 text-muted-foreground/30 mx-auto mb-2" />
                    <p className="text-xs text-muted-foreground">No notifications</p>
                  </div>
                ) : (
                  (notifications || []).slice(0, 20).map((n: any) => (
                    <button
                      key={n.id}
                      onClick={() => { if (!n.is_read) markRead.mutate(n.id); }}
                      className={`w-full text-left px-4 py-3 hover:bg-secondary/50 transition-colors ${!n.is_read ? "bg-amber/5" : ""}`}
                    >
                      <div className="flex items-start gap-2">
                        {!n.is_read && <div className="mt-1.5 h-2 w-2 rounded-full bg-amber shrink-0" />}
                        <div className="flex-1 min-w-0">
                          <p className="text-xs font-medium text-foreground truncate">{n.title}</p>
                          <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2">{n.message}</p>
                          <p className="text-[10px] text-muted-foreground mt-1">
                            {n.created_at ? new Date(n.created_at).toLocaleString() : ""}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Avatar */}
        {user && (
          <Avatar className="h-8 w-8 border-2 border-amber/30">
            <AvatarImage src={user.avatar_url} alt={user.name} />
            <AvatarFallback className="bg-amber/20 text-amber text-xs font-bold">
              {user.name?.charAt(0)?.toUpperCase()}
            </AvatarFallback>
          </Avatar>
        )}
      </div>
    </header>
  );
}
