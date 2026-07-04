"use client";

import { LogOut, Menu, Search, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { navigationIcons } from "@/components/icons";
import type { CurrentActor } from "@/lib/auth-data";
import { navItems } from "@/lib/demo-data";

type AppShellProps = {
  children: ReactNode;
  actor: CurrentActor;
};

export function AppShell({ actor, children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (pathname !== "/login" && actor.authEnabled && !actor.userId) {
      window.location.href = `/login?next=${encodeURIComponent(pathname)}`;
    }
  }, [actor.authEnabled, actor.userId, pathname]);

  if (pathname === "/login") {
    return <>{children}</>;
  }

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" }).catch(() => undefined);
    window.location.href = "/login";
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">
            PQ
          </div>
          <div>
            <strong>PQ-AI</strong>
            <span>Paint Intelligence</span>
          </div>
          <button
            className="icon-button mobile-only"
            aria-label="关闭菜单"
            onClick={() => setMobileOpen(false)}
          >
            <X />
          </button>
        </div>
        <nav className="main-nav" aria-label="主导航">
          <span className="nav-section-label">工作空间</span>
          {navItems.map((item) => {
            const Icon = navigationIcons[item.icon];
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                className={`nav-item ${active ? "nav-item-active" : ""}`}
                href={item.href}
                onClick={() => setMobileOpen(false)}
              >
                <Icon aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          <div className="system-state">
            <span className="live-dot" />
            <div>
              <strong>数据链路正常</strong>
              <span>最后同步 08:42:16</span>
            </div>
          </div>
          <div className="identity">
            <div className="avatar">{actor.displayName.slice(0, 1)}</div>
            <div>
              <strong>{actor.displayName}</strong>
              <span>{actor.roles[0] ?? "已认证用户"}</span>
            </div>
            <ShieldCheck aria-label="已认证" />
          </div>
          <button className="logout-button" onClick={() => void logout()}>
            <LogOut />
            退出登录
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            className="icon-button mobile-only"
            aria-label="打开菜单"
            onClick={() => setMobileOpen(true)}
          >
            <Menu />
          </button>
          <div className="search-control">
            <Search aria-hidden="true" />
            <input aria-label="全局搜索" placeholder="搜索车型、点位、程序或任务..." />
            <kbd>⌘ K</kbd>
          </div>
          <div className="topbar-context">
            <span>生产日</span>
            <strong>2026-06-10 · 白班</strong>
          </div>
        </header>
        <main>{children}</main>
      </div>
    </div>
  );
}
