"use client";
import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth";
import { Badge, EmptyState, Spinner, fmtDate } from "@/components/ui";
import type { KBArticle, KBSearchHit } from "@/lib/types";

const CATEGORIES = ["hardware", "software", "network", "access", "other"];

export default function KBPage() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<KBSearchHit[] | null>(null);
  const [articles, setArticles] = useState<KBArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expand, setExpand] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState("other");
  const [creating, setCreating] = useState(false);

  const isAdmin = user?.role === "admin";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.listArticles({ page: 1, size: 20 });
      setArticles(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load knowledge base");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const search = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!q.trim()) return setHits(null);
    try {
      const results = await api.kbSearch(q);
      setHits(results);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    }
  };

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await api.createArticle(title, body, category);
      setTitle("");
      setBody("");
      setCategory("other");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create article");
    } finally {
      setCreating(false);
    }
  };

  const remove = async (id: number) => {
    if (!window.confirm("Delete this article?")) return;
    try {
      await api.deleteArticle(id);
      if (hits) setHits(hits.filter((h) => h.article_id !== id));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete article");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Knowledge Base</h1>
        <p className="text-sm text-slate-500">Search self-service articles — results are ranked by AI semantic similarity.</p>
      </div>

      {error && <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

      <form onSubmit={search} className="card flex gap-2 p-4">
        <input
          className="input"
          placeholder="Search the knowledge base, e.g. 'reset password', 'VPN offline'..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button className="btn-primary shrink-0" type="submit">Search</button>
        {hits && (
          <button className="btn-secondary shrink-0" type="button" onClick={() => { setHits(null); setQ(""); }}>
            Clear
          </button>
        )}
      </form>

      {hits && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">Search results ({hits.length})</h2>
          {hits.length === 0 ? (
            <EmptyState title="No matching articles" hint="Try different keywords, or contact support." />
          ) : (
            hits.map((h) => (
              <button key={h.article_id} onClick={() => setExpand(expand === h.article_id ? null : h.article_id)}
                      className="card block w-full p-5 text-left transition hover:border-brand-300 hover:shadow-md">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium text-slate-900">{h.title}</span>
                  <span className="flex items-center gap-2">
                    {h.score !== undefined && <span className="text-xs text-slate-400">{Math.round(h.score * 100)}% match</span>}
                    <Badge tone="indigo">{h.category}</Badge>
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-500">{h.snippet}</p>
              </button>
            ))
          )}
        </section>
      )}

      <section>
        <h2 className="mb-3 text-sm font-semibold text-slate-900">Latest articles</h2>
        {loading ? (
          <Spinner />
        ) : articles.length === 0 ? (
          <EmptyState title="No articles yet" />
        ) : (
          <div className="space-y-3">
            {articles.map((a) => (
              <div key={a.id} className="card p-5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-900">{a.title}</span>
                    <Badge tone="indigo">{a.category}</Badge>
                    {hits && <span className="font-mono text-xs text-slate-400">#{a.id}</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Updated {fmtDate(a.updated_at)}</span>
                    {isAdmin && (
                      <button className="text-xs font-medium text-red-500 hover:underline" onClick={() => remove(a.id)}>
                        Delete
                      </button>
                    )}
                  </div>
                </div>
                <p className="mt-2 text-sm text-slate-600">{a.body}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {isAdmin && (
        <section className="card p-6">
          <h2 className="mb-4 text-sm font-semibold text-slate-900">Add article</h2>
          <form onSubmit={create} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="label">Title</label>
                <input className="input" required maxLength={255} placeholder="How to reset your password" value={title}
                       onChange={(e) => setTitle(e.target.value)} />
              </div>
              <div>
                <label className="label">Category</label>
                <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="label">Body</label>
              <textarea className="input min-h-32 resize-y" required minLength={10} placeholder="Step-by-step instructions..." value={body}
                        onChange={(e) => setBody(e.target.value)} />
            </div>
            <button className="btn-primary" disabled={creating}>{creating ? "Adding..." : "Add article"}</button>
          </form>
        </section>
      )}
    </div>
  );
}