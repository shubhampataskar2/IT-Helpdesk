export type Role = "employee" | "support" | "admin";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface DuplicateInfo {
  ticket_id?: number;
  ticket_number?: string;
  similarity?: number;
}

export interface CommentOut {
  id: number;
  body: string;
  author_name?: string;
  created_at: string;
}

export interface Ticket {
  id: number;
  number: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  category: string;
  ai_summary?: string;
  ai_suggested_fix?: string;
  ai_confidence?: number;
  ai_refined: boolean;
  creator_id: number;
  creator_name?: string;
  assignee_id?: number;
  assignee_name?: string;
  duplicate_of?: DuplicateInfo;
  first_response_at?: string;
  sla_response_due_at?: string;
  sla_resolve_due_at?: string;
  escalated: boolean;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
  closed_at?: string;
  comments?: CommentOut[];
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface KBArticle {
  id: number;
  title: string;
  body: string;
  category: string;
  created_at: string;
  updated_at: string;
}

export interface KBSearchHit {
  article_id: number;
  title: string;
  snippet: string;
  score?: number;
  category: string;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Overview {
  total: number;
  open_tickets: number;
  by_status: Record<string, number>;
  category_dist: Record<string, number>;
  priority_dist: Record<string, number>;
  avg_resolve_minutes?: number;
  duplicates: number;
  created_by_day: Record<string, number>;
  resolved_by_day: Record<string, number>;
}

export interface SlaStats {
  [priority: string]: {
    total: number;
    resolved: number;
    response_measured: number;
    response_compliance?: number;
    resolve_measured: number;
    resolve_compliance?: number;
  };
}

export interface EngineerStat {
  user_id: number;
  name: string;
  email: string;
  role: string;
  assigned: number;
  active: number;
  resolved: number;
  avg_resolve_minutes?: number;
}

export interface AuditEntry {
  id: number;
  action: string;
  entity_type: string;
  entity_id?: string;
  details?: Record<string, unknown>;
  actor_name?: string;
  created_at: string;
}