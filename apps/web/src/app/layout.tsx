import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import { getCurrentActor } from "@/lib/auth-data";

import "./globals.css";

export const metadata: Metadata = {
  title: "PQ-AI | 喷涂工艺与质量智能化闭环系统",
  description: "汽车涂装工艺参数、材料与漆膜质量 AI 闭环管理平台",
};

export const dynamic = "force-dynamic";

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const actor = await getCurrentActor();
  return (
    <html lang="zh-CN">
      <body>
        <AppShell actor={actor}>{children}</AppShell>
      </body>
    </html>
  );
}
