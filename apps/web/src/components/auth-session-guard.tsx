"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/lib/auth-context";

/**
 * 页面层：仅在明确未登录时跳转登录页。
 * 不在此处因接口抖动清 cookie；真正失效由 /api/auth/me 的 401 清会话。
 */
export function AuthSessionGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { actor } = useAuth();
  const isAuthPage = pathname === "/login" || pathname === "/register";

  useEffect(() => {
    if (isAuthPage || actor.isAuthenticated) return;
    const next = `${pathname}${typeof window !== "undefined" ? window.location.search : ""}`;
    router.replace(`/login?next=${encodeURIComponent(next || "/")}`);
  }, [actor.isAuthenticated, isAuthPage, pathname, router]);

  return <>{children}</>;
}
