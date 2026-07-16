"use client";

import { LogOut, Menu, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState, type ReactNode } from "react";

import { navigationIcons } from "@/components/icons";
import { ContextSelector } from "@/components/context-selector";
import { useAuth } from "@/lib/auth-context";
import { primaryRoleLabel } from "@/lib/display-labels";
import { navSections, type NavItem } from "@/lib/ui-data";
import { WorkspaceContextProvider } from "@/lib/workspace-context";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const { actor, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isAdmin = actor.roles.includes("ADMIN") || actor.permissions.includes("*");

  const visibleSections = useMemo(() => {
    if (isAdmin) return navSections;
    const actorRoles = new Set(actor.roles);
    return navSections
      .map((section) => {
        const items: NavItem[] = [...section.items];
        return {
          ...section,
          items: items.filter(
            (item) => item.href === pathname || !item.roles || item.roles.some((role) => actorRoles.has(role)),
          ),
        };
      })
      .filter((section) => section.items.length > 0);
  }, [actor.roles, isAdmin, pathname]);

  const isAuthPage = pathname === "/login" || pathname === "/register";
  const todayLabel = new Date().toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  });

  if (isAuthPage) {
    return (
      <div className="app-shell">
        <main className="auth-main">{children}</main>
      </div>
    );
  }

  return (
    <WorkspaceContextProvider>
      <div className="app-shell">
        <aside className={`sidebar ${mobileOpen ? "sidebar-open" : ""}`}>
          <div className="brand-block">
            <div className="brand-mark" aria-hidden="true">
              PQ
            </div>
            <div>
              <strong>PQ-AI</strong>
              <span>喷涂质量智能闭环</span>
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
            {visibleSections.map((section) => {
              const item = section.items[0];
              if (!item) return null;
              const Icon = navigationIcons[item.icon];
              const active = item.href.split("?")[0] === pathname;
              return (
                <Link
                  key={section.key}
                  className={`nav-item nav-item-flat ${active ? "nav-item-active" : ""}`}
                  href={item.href}
                  onClick={() => setMobileOpen(false)}
                >
                  <Icon aria-hidden="true" />
                  <span>{section.title}</span>
                </Link>
              );
            })}
            {actor.isAuthenticated && isAdmin ? (
              <Link
                className={`nav-item nav-item-flat ${pathname === "/security-admin" ? "nav-item-active" : ""}`}
                href="/security-admin"
                onClick={() => setMobileOpen(false)}
              >
                <ShieldCheck aria-hidden="true" />
                <span>用户与角色</span>
              </Link>
            ) : null}
          </nav>
          <div className="sidebar-foot">
            <div className="system-state">
              <span className="live-dot" />
              <div>
                <strong>系统可用</strong>
                <span>请以页面内实时数据为准</span>
              </div>
            </div>
            {actor.isAuthenticated ? (
              <div className="identity">
                <Link href="/profile" className="avatar-link">
                  <div className="avatar">{actor.displayName.slice(0, 1)}</div>
                </Link>
                <div>
                  <strong>{actor.displayName}</strong>
                  <span>{primaryRoleLabel(actor.roles)}</span>
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
                  <Link href="/login" className="text-link">
                    点击登录
                  </Link>
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
            <div className="topbar-context">
              <span>今天</span>
              <strong>{todayLabel}</strong>
            </div>
          </header>
          <ContextSelector />
          <main>{children}</main>
        </div>
      </div>
    </WorkspaceContextProvider>
  );
}
