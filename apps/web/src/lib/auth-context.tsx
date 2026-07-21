"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type AuthActor = {
  userId: string | null;
  username: string;
  displayName: string;
  roles: string[];
  permissions: string[];
  isAuthenticated: boolean;
};

type ApiActor = {
  user_id: string | null;
  username: string;
  display_name: string;
  roles: string[];
  permissions: string[];
};

type AuthContextValue = {
  actor: AuthActor;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (
    username: string,
    password: string,
    displayName: string,
    email?: string,
    department?: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  refreshActor: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export const ANON_ACTOR: AuthActor = {
  userId: null,
  username: "anonymous",
  displayName: "未登录",
  roles: [],
  permissions: [],
  isAuthenticated: false,
};

function mapActor(actor: ApiActor): AuthActor {
  return {
    userId: actor.user_id,
    username: actor.username,
    displayName: actor.display_name,
    roles: actor.roles,
    permissions: actor.permissions,
    isAuthenticated: Boolean(actor.user_id),
  };
}

async function readAuthResponse(response: Response, fallbackMessage: string): Promise<AuthActor> {
  const body = (await response.json().catch(() => ({}))) as { actor?: ApiActor; error?: string };
  if (!response.ok || !body.actor) {
    throw new Error(body.error ?? fallbackMessage);
  }
  return mapActor(body.actor);
}

export function AuthProvider({
  children,
  initialActor = ANON_ACTOR,
}: {
  children: ReactNode;
  initialActor?: AuthActor;
}) {
  const [actor, setActor] = useState<AuthActor>(initialActor);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    setError(null);
    setLoading(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      setActor(await readAuthResponse(response, "登录失败"));
    } catch (err) {
      const message = err instanceof Error ? err.message : "登录失败";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(
    async (
      username: string,
      password: string,
      displayName: string,
      email?: string,
      department?: string,
    ) => {
      setError(null);
      setLoading(true);
      try {
        const response = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username,
            password,
            display_name: displayName,
            email: email || null,
            department: department || null,
          }),
        });
        setActor(await readAuthResponse(response, "注册失败"));
      } catch (err) {
        const message = err instanceof Error ? err.message : "注册失败";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const logout = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const response = await fetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? "退出登录失败");
      }
      setActor(ANON_ACTOR);
    } catch (err) {
      setError(err instanceof Error ? err.message : "退出登录失败");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const refreshActor = useCallback(async () => {
    const response = await fetch("/api/auth/me", { cache: "no-store" });
    if (response.status === 401) {
      setActor(ANON_ACTOR);
      return;
    }
    if (!response.ok) {
      // 后端暂不可用：保留当前登录态，避免刷新/轮询把用户踢掉
      return;
    }
    setActor(await readAuthResponse(response, "无法刷新账号信息"));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ actor, loading, error, login, register, logout, refreshActor }),
    [actor, loading, error, login, register, logout, refreshActor],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
