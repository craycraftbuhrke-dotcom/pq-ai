import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import { AuthProvider } from "@/lib/auth-context";

import "./globals.css";

export const metadata: Metadata = {
  title: "PQ-AI | 喷涂工艺与质量智能化闭环系统",
  description: "汽车涂装工艺参数、材料与漆膜质量 AI 闭环管理平台",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <AuthProvider>
          <AppShell>{children}</AppShell>
        </AuthProvider>
      </body>
    </html>
  );
}
