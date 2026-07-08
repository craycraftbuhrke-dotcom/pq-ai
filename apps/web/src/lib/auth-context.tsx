"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type AuthActor = {
  userId: string | null;
  username: string;
  displayName: string;
  roles: string[];
  permissions: string[];
  isAuthenticated: boolean;
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
  setApiKey: (key: string) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const ANON_ACTOR: AuthActor = {
  userId: null,
  username: "anonymous",
  displayName: "未登录",
  roles: [],
  permissions: [],
  isAuthenticated: false,
};

// 认证总开关：与后端 API_AUTH_ENABLED / 前端 middleware 保持一致。
// 关闭时前端不再请求 /auth/me、不再要求 pq_api_key cookie，直接以"测试模式"身份放行。
const authEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

// 认证关闭时的"占位身份"，让 UI 里所有 isAuthenticated 判断视为已登录，展示"测试模式"字样。
const AUTH_DISABLED_ACTOR: AuthActor = {
  userId: null,
  username: "system",
  displayName: "测试模式（认证已关闭）",
  roles: ["SYSTEM"],
  permissions: ["*"],
  isAuthenticated: true,
};

function getApiKeyFromCookie(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function setApiKeyCookie(value: string) {
  document.cookie = `pq_api_key=${encodeURIComponent(value)};path=/;max-age=2592000;SameSite=Lax`;
}

function clearApiKeyCookie() {
  document.cookie = "pq_api_key=;path=/;max-age=0;SameSite=Lax";
}

async function fetchActor(apiKey: string): Promise<AuthActor> {
  const apiUrl =
    typeof window === "undefined"
      ? process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL
      : process.env.NEXT_PUBLIC_API_URL;

  if (!apiUrl || !apiKey) return ANON_ACTOR;

  try {
    const response = await fetch(`${apiUrl}/auth/me`, {
      headers: { "x-api-key": apiKey },
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) return ANON_ACTOR;
    const data = (await response.json()) as {
      user_id: string | null;
      username: string;
      display_name: string;
      roles: string[];
    };
    return {
      userId: data.user_id,
      username: data.username,
      displayName: data.display_name,
      roles: data.roles,
      permissions: [],
      isAuthenticated: Boolean(data.user_id),
    };
  } catch {
    return ANON_ACTOR;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // 认证关闭时直接以 AUTH_DISABLED_ACTOR 初始化，跳过首屏 /auth/me 请求（避免加载卡顿）
  const [actor, setActor] = useState<AuthActor>(authEnabled ? ANON_ACTOR : AUTH_DISABLED_ACTOR);
  const [loading, setLoading] = useState(authEnabled);
  const [error, setError] = useState<string | null>(null);

  const setApiKey = useCallback(async (key: string) => {
    if (key) {
      setApiKeyCookie(key);
      const next = await fetchActor(key);
      setActor(next);
    } else {
      clearApiKeyCookie();
      setActor(ANON_ACTOR);
    }
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      setError(null);
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      try {
        const response = await fetch(`${apiUrl}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        if (!response.ok) {
          const body = (await response.json().catch(() => ({}))) as { detail?: string };
          throw new Error(body.detail ?? "登录失败");
        }
        const data = (await response.json()) as {
          user_id: string;
          username: string;
          display_name: string;
          roles: string[];
          permissions: string[];
          api_key: string;
        };
        setApiKeyCookie(data.api_key);
        setActor({
          userId: data.user_id,
          username: data.username,
          displayName: data.display_name,
          roles: data.roles,
          permissions: data.permissions,
          isAuthenticated: true,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "登录失败");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

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
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      try {
        const response = await fetch(`${apiUrl}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, display_name: displayName, email, department }),
        });
        if (!response.ok) {
          const body = (await response.json().catch(() => ({}))) as { detail?: string };
          throw new Error(body.detail ?? "注册失败");
        }
        const data = (await response.json()) as {
          user_id: string;
          username: string;
          display_name: string;
          roles: string[];
          permissions: string[];
          api_key: string;
        };
        setApiKeyCookie(data.api_key);
        setActor({
          userId: data.user_id,
          username: data.username,
          displayName: data.display_name,
          roles: data.roles,
          permissions: data.permissions,
          isAuthenticated: true,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : "注册失败");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const logout = useCallback(async () => {
    const apiKey = getApiKeyFromCookie();
    if (apiKey) {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;
      try {
        await fetch(`${apiUrl}/auth/logout`, {
          method: "POST",
          headers: { "x-api-key": apiKey },
        });
      } catch {
        // best effort
      }
    }
    clearApiKeyCookie();
    setActor(ANON_ACTOR);
  }, []);

  useEffect(() => {
    // 认证关闭：不请求 /auth/me，保持 AUTH_DISABLED_ACTOR，直接结束加载。
    if (!authEnabled) {
      return;
    }
    const apiKey = getApiKeyFromCookie();
    if (!apiKey) {
      const timer = window.setTimeout(() => setLoading(false), 0);
      return () => window.clearTimeout(timer);
    }
    let cancelled = false;
    fetchActor(apiKey).then((next) => {
      if (cancelled) return;
      setActor(next);
      setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ actor, loading, error, login, register, logout, setApiKey }),
    [actor, loading, error, login, register, logout, setApiKey],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
