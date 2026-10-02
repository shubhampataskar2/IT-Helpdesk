"use client";
import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, clearTokens, readTokens, storeTokens } from "@/lib/api";
import type { Role, User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const refreshUser = useCallback(async () => {
    if (!readTokens()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email: string, password: string) => {
    const tokens = await api.login(email, password);
    storeTokens(tokens);
    const me = await api.me();
    setUser(me);
    setLoading(false);
    router.push("/");
    router.refresh();
  };

  const register = async (email: string, fullName: string, password: string) => {
    const tokens = await api.register(email, fullName, password);
    storeTokens(tokens);
    const me = await api.me();
    setUser(me);
    setLoading(false);
    router.push("/");
    router.refresh();
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    router.push("/login");
  };

  useEffect(() => {
    if (loading && !user && pathname !== "/login" && pathname !== "/register") return;
    if (!loading && !user && pathname !== "/login" && pathname !== "/register") {
      router.push("/login");
    }
  }, [loading, user, pathname, router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function hasRole(user: User | null, roles: Role[]): boolean {
  return !!user && roles.includes(user.role);
}