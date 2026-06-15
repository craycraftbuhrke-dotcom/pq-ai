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
  username: "unconfigured",
  displayName: "未连接",
  roles: ["未认证"],
  permissions: [],
  authEnabled: false,
};

export function apiRequestHeaders(): HeadersInit {
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
      headers: apiRequestHeaders(),
      signal: AbortSignal.timeout(2500),
    });
    if (!response.ok) {
      return fallbackActor;
    }
    const actor = (await response.json()) as ApiActor;
    return {
      userId: actor.user_id,
      username: actor.username,
      displayName: actor.display_name,
      roles: actor.roles,
      permissions: actor.permissions,
      authEnabled: actor.auth_enabled,
    };
  } catch {
    return fallbackActor;
  }
}
