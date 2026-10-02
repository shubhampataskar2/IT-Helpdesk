"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Badge, PriorityBadge, Spinner } from "@/components/ui";
import type { Ticket } from "@/lib/types";

export default function NewTicketPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState<Ticket | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const t = await api.createTicket(title, description);
      setPending(t);
      setTitle("");
      setDescription("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">New ticket</h1>
        <p className="text-sm text-slate-500">Describe your issue — the AI will triage, summarize and suggest a fix.</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={submit} className="card space-y-4 p-6">
          <div>
            <label className="label">Summary</label>
            <input className="input" required maxLength={200} placeholder="e.g. Cannot access company email" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label className="label">Details</label>
            <textarea className="input min-h-40 resize-y" required placeholder="What happened, what have you tried, any error messages..." value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          {error && <div className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>}
          <div className="flex gap-3">
            <button className="btn-primary" disabled={busy}>{busy ? "Submitting..." : "Create ticket"}</button>
            <button type="button" className="btn-secondary" onClick={() => router.push("/tickets")}>Cancel</button>
          </div>
        </form>

        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-900">AI analysis</h2>
            {busy && !pending && <Spinner label="Analyzing..." />}
            {pending ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <PriorityBadge priority={pending.priority} />
                  <Badge tone="indigo">{pending.category}</Badge>
                  <Badge tone={pending.ai_refined ? "green" : "amber"}>
                    confidence {(pending.ai_confidence ?? 0) * 100}%
                  </Badge>
                </div>
                {pending.ai_summary && (
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Summary</div>
                    <p className="mt-1 text-sm text-slate-700">{pending.ai_summary}</p>
                  </div>
                )}
                {pending.ai_suggested_fix && (
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Suggested fix</div>
                    <p className="mt-1 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-900">{pending.ai_suggested_fix}</p>
                  </div>
                )}
                {pending.duplicate_of?.ticket_number && (
                  <div className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
                    Detected duplicate of {pending.duplicate_of.ticket_number} ({Math.round((pending.duplicate_of.similarity ?? 0) * 100)}% similar). Support will review.
                  </div>
                )}
                <div className="text-xs text-slate-400">
                  Ticket {pending.number} saved. AI refinement continues in the background.
                </div>
                <button className="btn-primary" onClick={() => router.push(`/tickets/${pending.id}`)}>
                  View ticket
                </button>
              </div>
            ) : (
              <p className="text-sm text-slate-400">Create a ticket to see the AI triage here.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}