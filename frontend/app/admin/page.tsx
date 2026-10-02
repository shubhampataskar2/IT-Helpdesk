"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth";
import { Badge, EmptyState, Spinner, fmtDate } from "@/components/ui";
import type { AuditEntry, User } from "@/lib/types";

const ROLES = ["employee", "support", "admin"];

export default function AdminPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [u, a] = await Promise.all([
        api.users(),
        api.auditLogs({ action: actionFilter || undefined, page: 1, size: 50 }),
      ]);
      setUsers(u);
      setLogs(a.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load admin data (admin access required)");
    } finally {
      setLoading(false);
    }
  }, [actionFilter]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

  const changeRole = async (id: number, role: string) => {
    try {
      await api.updateRole(id, role as User["role"]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Role update failed");
    }
  };

  const toggleActive = async (u: User) => {
    try {
      await api.setActive(u.id, !u.is_active);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  };

  if (loading) return <Spinner />;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Admin</h1>
        <p className="text-sm text-slate-500">Manage users, roles and review the audit trail.</p>
      </div>

      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <section className="card overflow-hidden">
        <div className="border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Users</h2>
        </div>
        {users.length === 0 ? (
          <div className="p-5"><EmptyState title="No users" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="px-5 py-2">User</th>
                  <th className="px-3 py-2">Role</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Joined</th>
                  <th className="px-5 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-t border-slate-100">
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-900">{u.full_name}</div>
                      <div className="text-xs text-slate-400">{u.email}</div>
                    </td>
                    <td className="px-3 py-3">
                      <select className="input w-32" value={u.role} onChange={(e) => changeRole(u.id, e.target.value)}>
                        {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-3">
                      <Badge tone={u.is_active ? "green" : "slate"}>{u.is_active ? "active" : "disabled"}</Badge>
                    </td>
                    <td className="px-3 py-3 text-xs text-slate-500">{fmtDate(u.created_at)}</td>
                    <td className="px-5 py-3 text-right">
                      <button
                        className="text-xs font-medium text-slate-500 hover:text-brand-600"
                        onClick={() => toggleActive(u)}
                        disabled={u.id === user?.id}
                      >
                        {u.is_active ? "Disable" : "Enable"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="card overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
          <h2 className="text-sm font-semibold text-slate-900">Audit log</h2>
          <select className="input w-52" value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}>
            <option value="">All actions</option>
            <option value="auth.login">auth.login</option>
            <option value="ticket.create">ticket.create</option>
            <option value="ticket.refined">ticket.refined</option>
            <option value="ticket.assign">ticket.assign</option>
            <option value="ticket.status_update">ticket.status_update</option>
            <option value="user.role_update">user.role_update</option>
            <option value="user.active_update">user.active_update</option>
            <option value="kb.create">kb.create</option>
            <option value="kb.delete">kb.delete</option>
          </select>
        </div>
        {logs.length === 0 ? (
          <div className="p-5"><EmptyState title="No audit entries" /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-400">
                  <th className="px-5 py-2">Time</th>
                  <th className="px-3 py-2">Actor</th>
                  <th className="px-3 py-2">Action</th>
                  <th className="px-3 py-2">Target</th>
                  <th className="px-5 py-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l) => (
                  <tr key={l.id} className="border-t border-slate-100">
                    <td className="whitespace-nowrap px-5 py-2 text-xs text-slate-500">{fmtDate(l.created_at)}</td>
                    <td className="px-3 py-2 text-xs text-slate-700">{l.actor_name || "system"}</td>
                    <td className="px-3 py-2"><code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">{l.action}</code></td>
                    <td className="px-3 py-2 text-xs text-slate-500">{l.entity_type}{l.entity_id ? `#${l.entity_id}` : ""}</td>
                    <td className="max-w-64 truncate px-5 py-2 text-xs text-slate-500">{l.details ? JSON.stringify(l.details) : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}