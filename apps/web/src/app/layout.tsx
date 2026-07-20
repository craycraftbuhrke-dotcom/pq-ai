import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
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
    isAuthenticated: Boolean(currentActor.userId) || !currentActor.authEnabled,
  };

  return (
    <html lang="zh-CN">
      <body>
        <AuthProvider initialActor={initialActor}>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
