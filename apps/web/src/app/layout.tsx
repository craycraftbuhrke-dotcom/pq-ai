import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import { AuthSessionGuard } from "@/components/auth-session-guard";
import { AuthProvider, type AuthActor } from "@/lib/auth-context";
import { getCurrentActor } from "@/lib/auth-data";

import "./globals.css";

export const metadata: Metadata = {
  title: "PQ-AI | 喷涂工艺与质量智能化闭环系统",
  description: "汽车涂装工艺参数、材料与漆膜质量智能闭环管理平台",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const currentActor = await getCurrentActor();
  const initialActor: AuthActor = {
    userId: currentActor.userId,
    username: currentActor.username,
    displayName: currentActor.displayName,
    roles: currentActor.roles,
    permissions: currentActor.permissions,
    // cookie 仍在但后端暂不可用时，按已登录处理，避免刷新被当成退出
    isAuthenticated:
      Boolean(currentActor.userId) ||
      !currentActor.authEnabled ||
      Boolean(currentActor.sessionPresent),
  };

  return (
    <html lang="zh-CN">
      <body>
        <AuthProvider initialActor={initialActor}>
          <AuthSessionGuard>
            <AppShell>{children}</AppShell>
          </AuthSessionGuard>
        </AuthProvider>
      </body>
    </html>
  );
}
