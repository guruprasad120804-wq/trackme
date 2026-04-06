"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeftRight, Download, Filter, ChevronLeft, ChevronRight } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn, formatCurrency, formatDate, gainColor } from "@/lib/utils";
import { getTransactions } from "@/lib/api";

const TXN_COLORS: Record<string, string> = {
  buy: "bg-emerald-500/10 text-emerald-400",
  sip: "bg-emerald-500/10 text-emerald-400",
  sell: "bg-red-500/10 text-red-400",
  redemption: "bg-red-500/10 text-red-400",
  dividend: "bg-amber/10 text-amber",
  switch_in: "bg-blue-500/10 text-blue-400",
  switch_out: "bg-orange-500/10 text-orange-400",
};

export default function TransactionsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["transactions", page, search],
    queryFn: () =>
      getTransactions({
        page,
        page_size: 50,
        ...(search ? { search } : {}),
      }).then((r) => r.data),
  });

  const transactions = data?.items || [];
  const totalPages = data?.total_pages || 0;

  return (
    <div className="min-h-screen">
      <Header title="Transactions" subtitle="All your investment transactions" />

      <div className="p-6 space-y-4">
        {/* Filters */}
        <div className="flex items-center justify-between">
          <Input
            placeholder="Search by asset name..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="max-w-sm bg-secondary border-border"
          />
          <Button variant="outline" size="sm" className="border-border text-muted-foreground">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="text-left px-5 py-3 font-medium">Date</th>
                <th className="text-left px-5 py-3 font-medium">Asset</th>
                <th className="text-left px-5 py-3 font-medium">Type</th>
                <th className="text-right px-5 py-3 font-medium">Qty</th>
                <th className="text-right px-5 py-3 font-medium">Price</th>
                <th className="text-right px-5 py-3 font-medium">Amount</th>
                <th className="text-left px-5 py-3 font-medium">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading && [...Array(8)].map((_, i) => (
                <tr key={i}>
                  <td className="px-5 py-3"><Skeleton className="h-4 w-20" /></td>
                  <td className="px-5 py-3"><Skeleton className="h-4 w-28" /></td>
                  <td className="px-5 py-3"><Skeleton className="h-5 w-14 rounded-full" /></td>
                  <td className="px-5 py-3 text-right"><Skeleton className="h-4 w-14 ml-auto" /></td>
                  <td className="px-5 py-3 text-right"><Skeleton className="h-4 w-16 ml-auto" /></td>
                  <td className="px-5 py-3 text-right"><Skeleton className="h-4 w-20 ml-auto" /></td>
                  <td className="px-5 py-3"><Skeleton className="h-3 w-16" /></td>
                </tr>
              ))}
              {!isLoading && transactions.map((t: any, i: number) => (
                <motion.tr
                  key={t.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.02 }}
                  className="hover:bg-secondary/50 transition-colors"
                >
                  <td className="px-5 py-3 text-sm text-foreground">{formatDate(t.trade_date)}</td>
                  <td className="px-5 py-3 text-sm font-medium text-foreground">{t.asset_name}</td>
                  <td className="px-5 py-3">
                    <Badge className={cn("text-[10px] font-semibold capitalize", TXN_COLORS[t.type] || "bg-secondary text-muted-foreground")}>
                      {t.type.replace("_", " ")}
                    </Badge>
                  </td>
                  <td className="px-5 py-3 text-sm text-right text-foreground">{parseFloat(t.quantity).toFixed(3)}</td>
                  <td className="px-5 py-3 text-sm text-right text-foreground">{formatCurrency(t.price, 2)}</td>
                  <td className="px-5 py-3 text-sm text-right font-semibold text-foreground">{formatCurrency(t.amount)}</td>
                  <td className="px-5 py-3">
                    <span className="text-[10px] text-muted-foreground capitalize">{t.source || "—"}</span>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>

          {transactions.length === 0 && !isLoading && (
            <div className="p-12 text-center">
              <ArrowLeftRight className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">No transactions found</p>
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Page {page} of {totalPages} ({data?.total} total)
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="border-border"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="border-border"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
