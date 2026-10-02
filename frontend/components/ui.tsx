"use client";
import clsx from "clsx";
import type { ReactNode } from "react";

export function Badge({ children, tone }: { children: ReactNode; tone?: string }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-700",
    blue: "bg-blue-100 text-blue-700",
    green: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
    red: "bg-red-100 text-red-700",
    indigo: "bg-brand-50 text-brand-700",
  };
  return (
    <span className={clsx("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", tones[tone || "slate"])}>
      {children}
    </span>
  );
}

const STATUS_TONES: Record<string, string> = {
  open: "blue",
  in_progress: "amber",
  awaiting_response: "indigo",
  resolved: "green",
  closed: "slate",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONES[status] || "slate"}>{status.replace("_", " ")}</Badge>;
}

const PRIORITY_TONES: Record<string, string> = {
  low: "slate",
  medium: "blue",
  high: "amber",
  critical: "red",
};

export function PriorityBadge({ priority }: { priority: string }) {
  return <Badge tone={PRIORITY_TONES[priority] || "slate"}>{priority}</Badge>;
}

export function Spinner({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="flex items-center justify-center py-16 text-sm text-slate-400">
      <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600" />
      {label}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="card flex flex-col items-center justify-center py-16 text-center">
      <div className="text-sm font-medium text-slate-700">{title}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

export function StatCard({ label, value, accent }: { label: string; value: ReactNode; accent?: string }) {
  return (
    <div className="card px-5 py-4">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</div>
      <div className={clsx("mt-1 text-2xl font-bold", accent || "text-slate-900")}>{value}</div>
    </div>
  );
}

export function fmtDate(iso?: string): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function fmtMinutes(mins?: number): string {
  if (mins === undefined || mins === null) return "—";
  const h = Math.floor(mins / 60);
  const m = Math.round(mins % 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}