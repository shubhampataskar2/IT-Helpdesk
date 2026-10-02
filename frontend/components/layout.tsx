"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/auth";
import clsx from "clsx";
import type { ReactNode } from "react";

const NAV = [
  { href: "/", label: "Dashboard", roles: ["employee", "support", "admin"] },
  { href: "/tickets", label: "Tickets", roles: ["employee", "support", "admin"] },
  { href: "/tickets/new", label: "New Ticket", roles: ["employee", "support", "admin"] },
  { href: "/kb", label: "Knowledge Base", roles: ["employee", "support", "admin"] },
];

const STAFF_ONLY = [
  { href: "/admin", label: "Admin", roles: ["admin"] },
];

export function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return <>{children}</>;

  const items = [...NAV.filter((n) => n.roles.includes(user.role)), ...STAFF_ONLY.filter((n) => n.roles.includes(user.role))];

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-20 flex w-60 flex-col border-r border-slate-200 bg-white">
        <div className="flex h-16 items-center gap-2 border-b border-slate-200 px-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">IT</div>
          <div>
            <div className="text-sm font-semibold text-slate-900">IT Helpdesk</div>
            <div className="text-xs text-slate-400">AI-Powered</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {items.map((item) => {
            const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "block rounded-lg px-3 py-2 text-sm font-medium transition",
                  active ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-slate-200 px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="min-w-0">
              <div className="truncate text-sm font-medium text-slate-900">{user.full_name}</div>
              <div className="truncate text-xs text-slate-400">
                {user.email} · <span className="capitalize">{user.role}</span>
              </div>
            </div>
            <button onClick={logout} className="text-xs font-medium text-slate-400 hover:text-brand-600">
              Logout
            </button>
          </div>
        </div>
      </aside>
      <main className="pl-60">
        <div className="mx-auto max-w-6xl px-8 py-8">{children}</div>
      </main>
    </div>
  );
}