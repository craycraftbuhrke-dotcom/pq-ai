type CacheEntry = {
  expiresAt: number;
  value: unknown;
};

const store = new Map<string, CacheEntry>();

const DEFAULT_TTL_MS = 60_000;
const MASTER_DATA_TTL_MS = 5 * 60_000;
const OVERVIEW_TTL_MS = 45_000;

export function getCachedValue<T>(key: string): T | undefined {
  const hit = store.get(key);
  if (!hit) return undefined;
  if (hit.expiresAt <= Date.now()) {
    store.delete(key);
    return undefined;
  }
  return hit.value as T;
}

export function setCachedValue<T>(key: string, value: T, ttlMs = DEFAULT_TTL_MS): T {
  store.set(key, { expiresAt: Date.now() + Math.max(1_000, ttlMs), value });
  return value;
}

export function invalidateClientCache(prefix?: string): void {
  if (!prefix) {
    store.clear();
    return;
  }
  for (const key of store.keys()) {
    if (key.startsWith(prefix)) store.delete(key);
  }
}

export async function cachedJsonFetch<T>(
  path: string,
  options?: {
    ttlMs?: number;
    init?: RequestInit;
    key?: string;
  },
): Promise<T> {
  const key = options?.key ?? `get:${path}`;
  const cached = getCachedValue<T>(key);
  if (cached !== undefined) return cached;

  const response = await fetch(path, { cache: "no-store", ...options?.init });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { error?: unknown; detail?: unknown };
    const message =
      typeof payload.error === "string"
        ? payload.error
        : typeof payload.detail === "string"
          ? payload.detail
          : `请求失败（${response.status}）`;
    throw new Error(message);
  }
  const value = (await response.json()) as T;
  return setCachedValue(key, value, options?.ttlMs ?? DEFAULT_TTL_MS);
}

export async function cachedJsonFetchSoft<T>(
  path: string,
  fallback: T,
  options?: { ttlMs?: number; key?: string },
): Promise<T> {
  try {
    return await cachedJsonFetch<T>(path, options);
  } catch {
    return fallback;
  }
}

export const CLIENT_CACHE_TTL = {
  masterData: MASTER_DATA_TTL_MS,
  overview: OVERVIEW_TTL_MS,
  default: DEFAULT_TTL_MS,
} as const;
