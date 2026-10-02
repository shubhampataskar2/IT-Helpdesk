"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth";
import { EmptyState, PriorityBadge, Spinner, StatCard, StatusBadge, fmtDate, fmtMinutes } from "@/components/ui";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import type { EngineerStat, Overview, SlaStats } from "@/lib/types";

const PIE_COLORS = ["#6366f1", "#0ea5e9", "#f59e0b", "#ef4444", "#10b981", "#8b5cf6", "#ec4899"];

export default function DashboardPage() {
  const { user, loading: authLoading } = useAuth();
  const [ov, setOv] = useState<Overview | null>(null);
  const [sla, setSla] = useState<SlaStats | null>(null);
  const [engineers, setEngineers] = useState<EngineerStat[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [o, s, e] = await Promise.all([api.overview(), api.sla(), api.engineersStats()]);
      setOv(o);
      setSla(s);
      setEngineers(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    }
  }, []);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  if (authLoading || !user) return <Spinner />;

  const createdByDay = ov ? Object.entries(ov.created_by_day).map(([day, count]) => ({ day, created: count })) : [];
  const resolvedByDay = ov ? Object.entries(ov.resolved_by_day).map(([day, count]) => ({ day, resolved: count })) : [];
  const categoryDist = ov ? Object.entries(ov.category_dist).map(([name, value]) => ({ name: name || "uncategorized", value })) : [];
  const statusDist = ov
    ? Object.entries(ov.by_status).map(([name, value]) => ({ name: name.replace("_", " ") || "none", value }))
    : [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">Welcome back, {user.full_name}. Here is what is happening.</p>
        </div>
        <Link href="/tickets/new" className="btn-primary">Create ticket</Link>
      </div>

      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      {!ov ? (
        <Spinner />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Total tickets" value={ov.total} />
            <StatCard label="Open" value={ov.open_tickets} accent="text-amber-600" />
            <StatCard label="Resolved" value={ov.by_status.resolved || 0} accent="text-emerald-600" />
            <StatCard label="Avg resolve time" value={fmtMinutes(ov.avg_resolve_minutes)} />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="card p-5">
              <h2 className="mb-4 text-sm font-semibold text-slate-900">Tickets created vs resolved (last 14 days)</h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={createdByDay} barGap={2}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar name="Created" dataKey="created" fill="#6366f1" radius={[3, 3, 0, 0]} />
                  <Bar name="Resolved" dataKey="resolved" fill="#10b981" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </section>

            <section className="card p-5">
              <h2 className="mb-4 text-sm font-semibold text-slate-900">Tickets by status</h2>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={statusDist} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={90} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#4f46e5" radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </section>

            <section className="card p-5">
              <h2 className="mb-4 text-sm font-semibold text-slate-900">By category</h2>
              {categoryDist.length === 0 ? (
                <EmptyState title="No tickets yet" />
              ) : (
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={categoryDist} dataKey="value" nameKey="name" outerRadius={80}>
                      {categoryDist.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </section>

            <section className="card p-5">
              <h2 className="mb-4 text-sm font-semibold text-slate-900">SLA compliance by priority</h2>
              {!sla ? (
                <Spinner />
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                      <th className="pb-2">Priority</th>
                      <th className="pb-2">Total</th>
                      <th className="pb-2">Resp</th>
                      <th className="pb-2">Resolve</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(sla).map(([prio, s]) => (
                      <tr key={prio} className="border-t border-slate-100">
                        <td className="py-2"><PriorityBadge priority={prio} /></td>
                        <td className="px-2 py-2">{s.total}</td>
                        <td className="px-2 py-2">{s.response_compliance !== undefined ? `${Math.round(s.response_compliance)}%` : "—"}</td>
                        <td className="px-2 py-2">{s.resolve_compliance !== undefined ? `${Math.round(s.resolve_compliance)}%` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>

          <section className="card p-5">
            <h2 className="mb-4 text-sm font-semibold text-slate-900">Engineer performance</h2>
            {engineers.length === 0 ? (
              <EmptyState title="No engineers yet" hint="Promote users to support to see this report." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                      <th className="pb-2">Engineer</th>
                      <th className="pb-2">Assigned</th>
                      <th className="pb-2">Active</th>
                      <th className="pb-2">Resolved</th>
                      <th className="pb-2">Avg resolve</th>
                      <th className="pb-2">Last ticket</th>
                    </tr>
                  </thead>
                  <tbody>
                    {engineers.map((e) => (
                      <tr key={e.user_id} className="border-t border-slate-100">
                        <td className="py-2">
                          <div className="font-medium text-slate-900">{e.name}</div>
                          <div className="text-xs text-slate-400">{e.email}</div>
                        </td>
                        <td className="px-2 py-2">{e.assigned}</td>
                        <td className="px-2 py-2">{e.active}</td>
                        <td className="px-2 py-2 font-medium text-emerald-700">{e.resolved}</td>
                        <td className="px-2 py-2">{fmtMinutes(e.avg_resolve_minutes)}</td>
                        <td className="px-2 py-2">{fmtDate((e as unknown as { last_ticket_at?: string }).last_ticket_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <div className="grid gap-4 md:grid-cols-2">
            <StatCard label="Detected duplicates" value={ov.duplicates} accent="text-brand-600" />
            <StatCard label="Recent activity" value={`${(ov.created_by_day && Object.keys(ov.created_by_day).length) || 0} days`} />
          </div>
        </>
      )}
    </div>
  );
}