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
  /** Cookie 仍在，但后端暂时不可用——刷新时不应当成已退出 */
  sessionPresent?: boolean;
  connectionError?: string;
};

export type ApiActor = {
  user_id: string | null;
  username: string;
  display_name: string;
  roles: string[];
  permissions: string[];
  auth_enabled: boolean;
};

function isApiActor(value: unknown): value is ApiActor {
  if (!value || typeof value !== "object") return false;
  const actor = value as Partial<ApiActor>;
  return (
    (typeof actor.user_id === "string" || actor.user_id === null) &&
    typeof actor.username === "string" &&
    typeof actor.display_name === "string" &&
    Array.isArray(actor.roles) &&
    actor.roles.every((item) => typeof item === "string") &&
    Array.isArray(actor.permissions) &&
    actor.permissions.every((item) => typeof item === "string") &&
    typeof actor.auth_enabled === "boolean"
  );
}

async function parseApiActor(response: Response): Promise<ApiActor> {
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw Object.assign(new Error("后端认证服务返回了无法识别的结果"), { status: 502 });
  }
  if (!isApiActor(value)) {
    throw Object.assign(new Error("后端认证服务返回了不完整的账号信息"), { status: 502 });
  }
  return value;
}

// 默认启用认证；生产环境不能通过环境变量取得 SYSTEM 通配权限。
const authEnabledEnv = !(
  process.env.NODE_ENV === "test" &&
  process.env.AUTH_ENABLED === "false" &&
  process.env.API_AUTH_ENABLED === "false"
);

export function upstreamRequestSignal(request: Request, timeoutMs = 10_000): AbortSignal {
  return AbortSignal.any([request.signal, AbortSignal.timeout(timeoutMs)]);
}

export function isUpstreamTimeout(error: unknown): boolean {
  return error instanceof DOMException && error.name === "TimeoutError";
}

export async function requireApiActor(request: Request, permission?: string): Promise<ApiActor> {
  if (!authEnabledEnv) {
    return {
      user_id: "isolated-test-mode",
      username: "system",
      display_name: "测试模式（认证已关闭）",
      roles: ["SYSTEM"],
      permissions: ["*"],
      auth_enabled: false,
    };
  }
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) {
    throw Object.assign(new Error("后端认证服务未配置"), { status: 503 });
  }
  let response: Response;
  try {
    response = await fetch(`${apiUrl}/auth/me`, {
      headers: await apiRequestHeaders(request),
      cache: "no-store",
      signal: upstreamRequestSignal(request, 2500),
    });
  } catch (error) {
    throw Object.assign(
      new Error(isUpstreamTimeout(error) ? "后端认证服务响应超时" : "无法连接后端认证服务"),
      { status: isUpstreamTimeout(error) ? 504 : 502 },
    );
  }
  if (!response.ok) {
    if (response.status === 401) {
      throw Object.assign(new Error("登录已失效，请重新登录"), { status: 401 });
    }
    if (response.status === 403) {
      throw Object.assign(new Error("当前账号没有访问权限"), { status: 403 });
    }
    throw Object.assign(new Error("后端认证服务异常"), { status: response.status });
  }
  const actor = await parseApiActor(response);
  if (!actor.user_id) {
    throw Object.assign(new Error("请先登录"), { status: 401 });
  }
  if (
    permission &&
    !actor.permissions.includes("*") &&
    !actor.permissions.includes(permission)
  ) {
    throw Object.assign(new Error("当前账号没有执行此操作的权限"), { status: 403 });
  }
  return actor;
}

export async function requireApiPermission(request: Request, permission: string): Promise<ApiActor> {
  return requireApiActor(request, permission);
}

export const fallbackActor: CurrentActor = {
  userId: null,
  username: "anonymous",
  displayName: "未登录",
  roles: [],
  permissions: [],
  authEnabled: authEnabledEnv,
};

// 认证关闭时服务端组件展示的占位身份（避免"未登录"字样出现）
const authDisabledActor: CurrentActor = {
  userId: null,
  username: "system",
  displayName: "测试模式（认证已关闭）",
  roles: ["SYSTEM"],
  permissions: ["*"],
  authEnabled: false,
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

export async function apiRequestHeaders(request?: Request): Promise<HeadersInit> {
  const token = await sessionToken(request);
  if (token) return { Authorization: `Bearer ${token}` };
  return {};
}

export async function getCurrentActor(): Promise<CurrentActor> {
  // 认证关闭：直接返回占位身份，不再请求后端 /auth/me，避免测试期无网络也能进入系统。
  if (!authEnabledEnv) {
    return authDisabledActor;
  }
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  const token = await sessionToken();
  if (!apiUrl) {
    return token
      ? {
          ...fallbackActor,
          sessionPresent: true,
          displayName: "已登录（API 未配置）",
          connectionError: "后端 API 地址未配置",
        }
      : withConnectionError("后端 API 地址未配置");
  }
  if (!token) {
    return fallbackActor;
  }
  try {
    const response = await fetch(`${apiUrl}/auth/me`, {
      cache: "no-store",
      headers: { Authorization: `Bearer ${token}` },
      // 与登录态代理一致：给慢库留足时间，避免刷新时误判
      signal: AbortSignal.timeout(5000),
    });
    if (response.status === 401) {
      // 会话明确失效；cookie 清理由 /api/auth/me 或登出接口负责
      return fallbackActor;
    }
    if (!response.ok) {
      const payload = (await response.json().catch(() => ({}))) as ApiErrorPayload;
      return {
        ...fallbackActor,
        sessionPresent: true,
        displayName: "已登录（服务恢复中）",
        connectionError:
          stringifyApiError(payload.detail) ??
          stringifyApiError(payload.error) ??
          `后端认证接口暂时不可用（HTTP ${response.status}）`,
      };
    }
    return mapActor(await parseApiActor(response));
  } catch (error) {
    const message = error instanceof Error ? error.message : "无法连接后端认证接口";
    return {
      ...fallbackActor,
      sessionPresent: true,
      displayName: "已登录（服务恢复中）",
      connectionError: `无法连接后端认证接口：${message}`,
    };
  }
}
