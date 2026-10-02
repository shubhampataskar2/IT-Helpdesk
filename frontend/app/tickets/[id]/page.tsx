"use client";
import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth";
import { Badge, EmptyState, PriorityBadge, Spinner, StatusBadge, fmtDate, fmtMinutes } from "@/components/ui";
import clsx from "clsx";
import type { Ticket, User } from "@/lib/types";

const ROLE_RANK: Record<string, number> = { employee: 0, support: 1, admin: 2 };

const TRANSITIONS: Array<{ from: string; to: string; minRole: string; ownerOnly?: boolean }> = [
  { from: "new", to: "open", minRole: "support" },
  { from: "new", to: "closed", minRole: "admin" },
  { from: "new", to: "in_progress", minRole: "support" },
  { from: "new", to: "resolved", minRole: "support" },
  { from: "open", to: "in_progress", minRole: "support" },
  { from: "open", to: "resolved", minRole: "support" },
  { from: "open", to: "closed", minRole: "admin" },
  { from: "in_progress", to: "resolved", minRole: "support" },
  { from: "in_progress", to: "new", minRole: "support" },
  { from: "in_progress", to: "closed", minRole: "admin" },
  { from: "resolved", to: "closed", minRole: "support" },
  { from: "resolved", to: "open", minRole: "employee", ownerOnly: true },
];

const TRANSITION_LABEL: Record<string, string> = {
  open: "Accept",
  in_progress: "Start work",
  resolved: "Mark resolved",
  closed: "Close",
  new: "Back to new",
};

export default function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [engineers, setEngineers] = useState<User[]>([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const isStaff = user && user.role !== "employee";
  const isOwner = ticket && user && ticket.creator_id === user.id;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [t, eng] = await Promise.all([api.getTicket(Number(id)), isStaff ? api.engineers() : Promise.resolve([])]);
      setTicket(t);
      setEngineers(eng);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ticket");
    } finally {
      setLoading(false);
    }
  }, [id, isStaff]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const act = async <T,>(fn: Promise<T>) => {
    try {
      await fn;
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  };

  if (loading || !user) return <Spinner />;
  if (!ticket) return <EmptyState title={error || "Ticket not found"} />;

  const actions = TRANSITIONS.filter(
    (t) =>
      t.from === ticket.status &&
      (t.ownerOnly ? isOwner && ROLE_RANK[user.role] >= ROLE_RANK[t.minRole] : ROLE_RANK[user.role] >= ROLE_RANK[t.minRole])
  );

  return (
    <div className="space-y-6">
      <button onClick={() => router.back()} className="text-sm font-medium text-brand-600 hover:underline">← Back to tickets</button>

      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <div className="card p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-xs text-slate-400">{ticket.number}</span>
              <h1 className="text-xl font-bold text-slate-900">{ticket.title}</h1>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <StatusBadge status={ticket.status} />
              <PriorityBadge priority={ticket.priority} />
              <Badge tone="indigo">{ticket.category}</Badge>
              {ticket.escalated && <Badge tone="red">escalated</Badge>}
              {ticket.duplicate_of && <Badge tone="red">duplicate of {ticket.duplicate_of.ticket_number}</Badge>}
            </div>
          </div>
          <div className="text-right text-xs text-slate-400">
            <div>Opened {fmtDate(ticket.created_at)} by <span className="font-medium text-slate-600">{ticket.creator_name}</span></div>
            <div>Assignee: <span className="font-medium text-slate-600">{ticket.assignee_name || "Unassigned"}</span></div>
          </div>
        </div>
        <p className="mt-4 whitespace-pre-wrap rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-700">{ticket.description}</p>

        <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-lg bg-slate-50 px-3 py-2">
            <div className="text-xs text-slate-400">First response SLA</div>
            <div className={clsx("text-sm font-medium", ticket.escalated ? "text-red-600" : "text-slate-800")}>{fmtDate(ticket.sla_response_due_at)}</div>
          </div>
          <div className="rounded-lg bg-slate-50 px-3 py-2">
            <div className="text-xs text-slate-400">Resolution SLA</div>
            <div className="text-sm font-medium text-slate-800">{fmtDate(ticket.sla_resolve_due_at)}</div>
          </div>
          <div className="rounded-lg bg-slate-50 px-3 py-2">
            <div className="text-xs text-slate-400">First response</div>
            <div className="text-sm font-medium text-slate-800">{fmtDate(ticket.first_response_at)}</div>
          </div>
          <div className="rounded-lg bg-slate-50 px-3 py-2">
            <div className="text-xs text-slate-400">Closed</div>
            <div className="text-sm font-medium text-slate-800">{fmtDate(ticket.resolved_at || ticket.closed_at)}</div>
          </div>
        </div>

        {(ticket.ai_refined || ticket.ai_summary || ticket.ai_suggested_fix) && (
          <div className="mt-6 space-y-3 rounded-lg border border-brand-100 bg-brand-50/50 p-4">
            <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              AI analysis · {Math.round((ticket.ai_confidence ?? 0) * 100)}% confidence
            </div>
            {ticket.ai_summary && <p className="text-sm text-slate-700"><span className="font-medium">Summary:</span> {ticket.ai_summary}</p>}
            {ticket.ai_suggested_fix && (
              <div className="rounded-lg bg-white px-3 py-2 text-sm text-slate-700">
                <span className="font-medium text-emerald-700">Suggested fix:</span> {ticket.ai_suggested_fix}
              </div>
            )}
          </div>
        )}

        {isStaff && (
          <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
            {actions.map((a) => (
              <button
                key={a.to}
                className={clsx(
                  "rounded-lg px-4 py-2 text-sm font-medium",
                  a.to === "closed" ? "border border-red-200 bg-red-50 text-red-700 hover:bg-red-100" : "bg-brand-600 text-white hover:bg-brand-700"
                )}
                onClick={() => act(api.updateTicket(ticket.id, { status: a.to }))}
              >
                {a.to === "open" && a.from === "resolved" ? "Reopen" : TRANSITION_LABEL[a.to] || a.to}
              </button>
            ))}
            <select
              className="input w-56"
              value={ticket.assignee_id ?? ""}
              onChange={(e) => act(api.assignTicket(ticket.id, e.target.value ? Number(e.target.value) : undefined))}
            >
              <option value="">Unassigned</option>
              {engineers.map((en) => (
                <option key={en.id} value={en.id}>{en.full_name}</option>
              ))}
            </select>
          </div>
        )}

        {!isStaff && isOwner && actions.length > 0 && (
          <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-4">
            {actions.map((a) => (
              <button key={a.to} className="btn-secondary" onClick={() => act(api.updateTicket(ticket.id, { status: a.to }))}>
                {a.to === "open" && a.from === "resolved" ? "Reopen" : TRANSITION_LABEL[a.to] || a.to}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="card p-6">
        <h2 className="mb-4 text-sm font-semibold text-slate-900">Comments ({ticket.comments?.length || 0})</h2>
        {(ticket.comments?.length || 0) === 0 ? (
          <p className="text-sm text-slate-400">No comments yet.</p>
        ) : (
          <div className="space-y-4">
            {ticket.comments?.map((c) => (
              <div key={c.id} className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="font-medium text-slate-600">{c.author_name || "System"}</span>
                  <span>{fmtDate(c.created_at)}</span>
                </div>
                <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{c.body}</p>
              </div>
            ))}
          </div>
        )}
        <form
          className="mt-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!comment.trim()) return;
            act(api.commentTicket(ticket.id, comment).then(() => setComment("")));
          }}
        >
          <input className="input" placeholder="Add a comment..." value={comment} onChange={(e) => setComment(e.target.value)} />
          <button className="btn-primary" type="submit">Post</button>
        </form>
      </div>
    </div>
  );
}