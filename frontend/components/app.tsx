"use client";
import { usePathname } from "next/navigation";
import { useAuth } from "@/components/auth";
import { Shell } from "@/components/layout";
import type { ReactNode } from "react";

const BARE_ROUTES = new Set(["/login", "/register"]);

export function AppShell({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();

  if (BARE_ROUTES.has(pathname)) return <>{children}</>;
  if (loading || !user) return <>{children}</>;
  return <Shell>{children}</Shell>;
}