import type {
  AuditEntry,
  EngineerStat,
  KBArticle,
  KBSearchHit,
  Overview,
  Page,
  Role,
  SlaStats,
  Ticket,
  Tokens,
  User,
} from "./types";

export const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") + "/api/v1";

const ACCESS_KEY = "helpdesk.access";
const REFRESH_KEY = "helpdesk.refresh";

export function readTokens(): Tokens | null {
  if (typeof window === "undefined") return null;
  const access = window.localStorage.getItem(ACCESS_KEY);
  const refresh = window.localStorage.getItem(REFRESH_KEY);
  return access && refresh ? { access_token: access, refresh_token: refresh, token_type: "bearer" } : null;
}

export function storeTokens(tokens: Tokens) {
  window.localStorage.setItem(ACCESS_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens() {
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
}

async function request<T>(path: string, options: {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  authenticated?: boolean;
  refreshIfExpired?: boolean;
} = {}): Promise<T> {
  const { method = "GET", body, params, authenticated = true, refreshIfExpired = true } = options;
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
    });
  }

  const doFetch = async (token?: string) =>
    fetch(url.toString(), {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

  let resp = await doFetch(authenticated ? readTokens()?.access_token : undefined);

  if (resp.status === 401 && authenticated && refreshIfExpired) {
    const tokens = readTokens();
    if (tokens) {
      const refreshed = await tryRefresh(tokens.refresh_token);
      if (refreshed) {
        resp = await doFetch(refreshed.access_token);
      }
    }
  }

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const data = await resp.json();
      if (typeof data === "object" && data !== null) {
        detail = Array.isArray(data.detail)
          ? data.detail.map((d: { msg?: string }) => d.msg || "").join("; ")
          : data.detail || detail;
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

async function tryRefresh(refreshToken: string): Promise<Tokens | null> {
  try {
    const resp = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) throw new Error("refresh failed");
    const data = (await resp.json()) as Tokens;
    storeTokens(data);
    return data;
  } catch {
    clearTokens();
    return null;
  }
}

// ---------------- Auth ----------------
export const api = {
  login: (email: string, password: string) =>
    request<Tokens>("/auth/login", { method: "POST", body: { email, password }, authenticated: false }),
  register: (email: string, full_name: string, password: string) =>
    request<Tokens>("/auth/register", { method: "POST", body: { email, full_name, password }, authenticated: false }),
  me: () => request<User>("/auth/me"),

  // ---------------- Tickets ----------------
  createTicket: (title: string, description: string) =>
    request<Ticket>("/tickets", { method: "POST", body: { title, description } }),
  listTickets: (params: Record<string, string | number | boolean | undefined>) =>
    request<Page<Ticket>>("/tickets", { params }),
  getTicket: (id: number) => request<Ticket>(`/tickets/${id}`),
  updateTicket: (id: number, body: Record<string, unknown>) =>
    request<Ticket>(`/tickets/${id}`, { method: "PATCH", body }),
  assignTicket: (id: number, assigneeId?: number) =>
    request<Ticket>(`/tickets/${id}/assign`, { method: "POST", body: { assignee_id: assigneeId ?? null } }),
  resolveTicket: (id: number) => request<Ticket>(`/tickets/${id}/resolve`, { method: "POST" }),
  reopenTicket: (id: number) => request<Ticket>(`/tickets/${id}/reopen`, { method: "POST" }),
  commentTicket: (id: number, body: string) =>
    request(`/tickets/${id}/comments`, { method: "POST", body: { body } }),

  // ---------------- Users / RBAC ----------------
  users: () => request<User[]>("/users"),
  engineers: () => request<User[]>("/users/engineers"),
  updateRole: (id: number, role: Role) => request<User>(`/users/${id}/role`, { method: "PATCH", body: { role } }),
  setActive: (id: number, is_active: boolean) =>
    request<User>(`/users/${id}/active`, { method: "PATCH", body: { is_active } }),

  // ---------------- Knowledge base ----------------
  createArticle: (title: string, body: string, category: string) =>
    request<KBArticle>("/kb", { method: "POST", body: { title, body, category } }),
  listArticles: (params: Record<string, string | number | undefined>) => request<Page<KBArticle>>("/kb", { params }),
  kbSearch: (q: string) => request<KBSearchHit[]>("/kb/search", { params: { q } }),
  deleteArticle: (id: number) => request(`/kb/${id}`, { method: "DELETE" }),

  // ---------------- Analytics / admin ----------------
  overview: () => request<Overview>("/analytics/overview"),
  sla: () => request<SlaStats>("/analytics/sla"),
  engineersStats: () => request<EngineerStat[]>("/analytics/engineers"),
  auditLogs: (params: Record<string, string | number | undefined>) => request<{ items: AuditEntry[]; total: number }>("/admin/audit-logs", { params }),
};