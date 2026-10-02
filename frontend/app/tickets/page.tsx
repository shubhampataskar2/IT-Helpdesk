"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth";
import { EmptyState, PriorityBadge, Spinner, StatusBadge, fmtDate } from "@/components/ui";
import clsx from "clsx";
import type { Ticket } from "@/lib/types";

const STATUSES = ["new", "open", "in_progress", "resolved", "closed"];
const PRIORITIES = ["low", "medium", "high", "critical"];
const CATEGORIES = ["access", "network", "hardware", "software", "other"];

export default function TicketsPage() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [category, setCategory] = useState("");
  const [mine, setMine] = useState(false);
  const [q, setQ] = useState("");

  const isStaff = user && user.role !== "employee";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listTickets({
        status,
        priority,
        category,
        q,
        mine: mine || undefined,
        page: 1,
        size: 50,
      });
      setTickets(res.items);
      setTotal(res.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, [status, priority, category, mine, q]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Tickets</h1>
          <p className="text-sm text-slate-500">{total} ticket{total === 1 ? "" : "s"}</p>
        </div>
        <Link href="/tickets/new" className="btn-primary">New ticket</Link>
      </div>

      <div className="card flex flex-wrap items-end gap-3 p-4">
        <div className="min-w-40 flex-1">
          <label className="label">Search</label>
          <input className="input" placeholder="Search title & description..." value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div>
          <label className="label">Status</label>
          <select className="input w-40" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Priority</label>
          <select className="input w-36" value={priority} onChange={(e) => setPriority(e.target.value)}>
            <option value="">All</option>
            {PRIORITIES.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Category</label>
          <select className="input w-36" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="label">View</label>
          <select className="input w-36" value={mine ? "mine" : "all"} onChange={(e) => setMine(e.target.value === "mine")}>
            <option value="all">Everyone</option>
            <option value="mine">{isStaff ? "Assigned to me" : "Created by me"}</option>
          </select>
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {loading ? (
        <Spinner />
      ) : tickets.length === 0 ? (
        <EmptyState title="No tickets match" hint="Try clearing filters or create a new ticket." />
      ) : (
        <div className="space-y-3">
          {tickets.map((t) => (
            <Link key={t.id} href={`/tickets/${t.id}`} className="card block p-5 transition hover:border-brand-300 hover:shadow-md">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-slate-400">{t.number}</span>
                  <span className="font-medium text-slate-900">{t.title}</span>
                  {t.duplicate_of && <span className="rounded bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600">duplicate</span>}
                </div>
                <div className="flex items-center gap-2">
                  <PriorityBadge priority={t.priority} />
                  <StatusBadge status={t.status} />
                </div>
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400">
                <span className="capitalize">#{t.category}</span>
                <span>{t.creator_name}</span>
                <span>{fmtDate(t.created_at)}</span>
                {t.assignee_name && <span>→ {t.assignee_name}</span>}
                {t.escalated && <span className="font-semibold text-red-500">escalated</span>}
                {t.sla_response_due_at && (
                  <span className={clsx(t.escalated && "text-red-500")}>
                    SLA due {fmtDate(t.sla_response_due_at)}
                  </span>
                )}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}