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

export async function apiRequestHeaders(request?: Request): Promise<HeadersInit> {
  const token = await sessionToken(request);
  if (token) return { Authorization: `Bearer ${token}` };

  const apiKey = process.env.API_KEY;
  return apiKey ? { "x-api-key": apiKey } : {};
}

export async function getCurrentActor(): Promise<CurrentActor> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    return fallbackActor;
  }
  try {
    const response = await fetch(`${apiUrl}/auth/me`, {
      cache: "no-store",
      headers: await apiRequestHeaders(),
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) {
      return fallbackActor;
    }
    return mapActor((await response.json()) as ApiActor);
  } catch {
    return fallbackActor;
  }
}
