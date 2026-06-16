"use client";

import { LogOut, Menu, Search, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

import { navigationIcons } from "@/components/icons";
import { ContextSelector } from "@/components/context-selector";
import { useAuth } from "@/lib/auth-context";
import { navItems } from "@/lib/demo-data";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const { actor, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isAuthPage = pathname === "/login" || pathname === "/register";

  if (isAuthPage) {
    return (
      <div className="app-shell">
        <main className="auth-main">{children}</main>
      </div>
    );
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
          {actor.isAuthenticated && (actor.roles.includes("ADMIN") || actor.permissions.includes("*")) ? (
            <Link
              className={`nav-item ${pathname === "/security-admin" ? "nav-item-active" : ""}`}
              href="/security-admin"
              onClick={() => setMobileOpen(false)}
            >
              <ShieldCheck aria-hidden="true" />
              <span>安全管理</span>
            </Link>
          ) : null}
        </nav>
        <div className="sidebar-foot">
          <div className="system-state">
            <span className="live-dot" />
            <div>
              <strong>数据链路正常</strong>
              <span>最后同步 08:42:16</span>
            </div>
          </div>
          {actor.isAuthenticated ? (
            <div className="identity">
              <Link href="/profile" className="avatar-link">
                <div className="avatar">{actor.displayName.slice(0, 1)}</div>
              </Link>
              <div>
                <strong>{actor.displayName}</strong>
                <span>{actor.roles[0] ?? "已认证用户"}</span>
              </div>
              <button
                className="icon-button"
                aria-label="退出登录"
                onClick={() => void logout()}
                title="退出登录"
              >
                <LogOut />
              </button>
            </div>
          ) : (
            <div className="identity">
              <div className="avatar">?</div>
              <div>
                <strong>未登录</strong>
                <Link href="/login" className="text-link">点击登录</Link>
              </div>
            </div>
          )}
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
        <ContextSelector />
        <main>{children}</main>
      </div>
    </div>
  );
}
