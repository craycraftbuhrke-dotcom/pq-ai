"use client";

import { LogOut, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState, type ReactNode } from "react";

import { navigationIcons } from "@/components/icons";
import { ContextSelector } from "@/components/context-selector";
import { SystemStatus } from "@/components/system-status";
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
  async function handleLogout() {
    try {
      await logout();
      window.location.replace("/login");
    } catch {
      // AuthProvider 保留当前身份并记录错误，避免失败时伪装成已退出。
    }
  }

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
          </nav>
          <div className="sidebar-foot">
            <SystemStatus />
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
                  onClick={() => void handleLogout()}
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
            <strong className="mobile-only">当前作业范围</strong>
          </header>
          <ContextSelector />
          <main>{children}</main>
        </div>
      </div>
    </WorkspaceContextProvider>
  );
}
