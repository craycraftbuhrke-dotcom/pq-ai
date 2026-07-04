import "server-only";

import { cookies } from "next/headers";

export const sessionCookieName = "pq_ai_session";

export type CurrentActor = {
  userId: string | null;
  username: string;
  displayName: string;
  roles: string[];
  permissions: string[];
  authEnabled: boolean;
  connectionError?: string;
};

type ApiActor = {
  user_id: string | null;
  username: string;
  display_name: string;
  roles: string[];
  permissions: string[];
  auth_enabled: boolean;
};

export const fallbackActor: CurrentActor = {
  userId: null,
  username: "anonymous",
  displayName: "未登录",
  roles: [],
  permissions: [],
  authEnabled: process.env.API_AUTH_ENABLED === "true",
};

type ApiErrorPayload = {
  detail?: unknown;
  error?: unknown;
};

function mapActor(actor: ApiActor): CurrentActor {
  return {
    userId: actor.user_id,
    username: actor.username,
    displayName: actor.display_name,
    roles: actor.roles,
    permissions: actor.permissions,
    authEnabled: actor.auth_enabled,
  };
}

function cookieFromHeader(headerValue: string | null, name: string): string | null {
  if (!headerValue) return null;
  const prefix = `${name}=`;
  const pair = headerValue
    .split(";")
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix));
  return pair ? decodeURIComponent(pair.slice(prefix.length)) : null;
}

async function sessionToken(request?: Request): Promise<string | null> {
  if (request) {
    return cookieFromHeader(request.headers.get("cookie"), sessionCookieName);
  }
  const store = await cookies();
  return store.get(sessionCookieName)?.value ?? null;
}

function stringifyApiError(value: unknown): string | undefined {
  if (typeof value === "string") return value;
  if (Array.isArray(value) || (value && typeof value === "object")) {
    return JSON.stringify(value);
  }
  return undefined;
}

function withConnectionError(message: string): CurrentActor {
  return { ...fallbackActor, connectionError: message };
}

async function apiKeyFromRequest(request?: Request): Promise<string | null> {
  if (request) {
    return cookieFromHeader(request.headers.get("cookie"), "pq_api_key");
  }
  const store = await cookies();
  return store.get("pq_api_key")?.value ?? null;
}

export async function apiRequestHeaders(request?: Request): Promise<HeadersInit> {
  const token = await sessionToken(request);
  if (token) return { Authorization: `Bearer ${token}` };

  const cookieApiKey = await apiKeyFromRequest(request);
  if (cookieApiKey) return { "x-api-key": cookieApiKey };

  const apiKey = process.env.API_KEY;
  return apiKey ? { "x-api-key": apiKey } : {};
}

export async function getCurrentActor(): Promise<CurrentActor> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return withConnectionError("后端 API 地址未配置");
  }
  try {
    const response = await fetch(`${apiUrl}/auth/me`, {
      cache: "no-store",
      headers: await apiRequestHeaders(),
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
      return withConnectionError(
        stringifyApiError(payload.detail) ??
          stringifyApiError(payload.error) ??
          `后端认证接口返回错误（HTTP ${response.status}）`,
      );
    }
    return mapActor((await response.json()) as ApiActor);
  } catch (error) {
    const message = error instanceof Error ? error.message : "无法连接后端认证接口";
    return withConnectionError(`无法连接后端认证接口：${message}`);
  }
}
