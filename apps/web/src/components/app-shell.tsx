"use client";

import { ChevronDown, LogOut, Menu, Search, ShieldCheck, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo, useState, type ReactNode } from "react";

import { navigationIcons } from "@/components/icons";
import { ContextSelector } from "@/components/context-selector";
import { useAuth } from "@/lib/auth-context";
import { navSections, roleQuickAccess, type NavItem } from "@/lib/ui-data";

type AppShellProps = {
  children: ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const { actor, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isAdmin = actor.roles.includes("ADMIN") || actor.permissions.includes("*");
  const isQualityFocused =
    actor.roles.includes("QUALITY_ENGINEER") && !actor.roles.includes("PROCESS_ENGINEER") && !isAdmin;

  const allNavItems = useMemo(() => {
    const items: NavItem[] = navSections.flatMap((section) => [...section.items]);
    return isAdmin
      ? [...items, { href: "/security-admin", label: "权限与安全", icon: "audit" } satisfies NavItem]
      : items;
  }, [isAdmin]);

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

  const quickAccessItems = useMemo(() => {
    const preferredPaths = actor.roles.flatMap((role) => roleQuickAccess[role] ?? []);
    const candidatePaths = preferredPaths.length
      ? preferredPaths
      : ["/", "/production", "/quality", "/engineering", "/master-data"];
    const uniquePaths = [...new Set(candidatePaths)];
    return uniquePaths
      .map((href) => allNavItems.find((item) => item.href === href))
      .filter((item): item is NavItem => Boolean(item))
      .filter((item) =>
        isAdmin
          ? true
          : visibleSections.some((section) => section.items.some((sectionItem) => sectionItem.href === item.href)),
      )
      .slice(0, 5);
  }, [actor.roles, allNavItems, isAdmin, visibleSections]);

  const initialCollapsedSections = useMemo(() => {
    const collapsed: Record<string, boolean> = {};
    for (const section of visibleSections) {
      if (section.key === "governance") {
        collapsed[section.key] = !isAdmin;
        continue;
      }
      if (section.key === "execution") {
        collapsed[section.key] = isQualityFocused;
        continue;
      }
      collapsed[section.key] = false;
    }
    return collapsed;
  }, [isAdmin, isQualityFocused, visibleSections]);

  const [collapsedOverrides, setCollapsedOverrides] = useState<Record<string, boolean>>({});

  function toggleSection(sectionKey: string) {
    const defaultValue = initialCollapsedSections[sectionKey] ?? false;
    const currentValue = collapsedOverrides[sectionKey] ?? defaultValue;
    setCollapsedOverrides((current) => ({
      ...current,
      [sectionKey]: !currentValue,
    }));
  }

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
          <span className="nav-section-label nav-root-label">工作空间</span>
          {quickAccessItems.length ? (
            <div className="nav-group nav-quick-group">
              <div className="nav-group-header">
                <div className="nav-section-copy">
                  <span className="nav-section-label">常用入口</span>
                  <span className="nav-section-description">结合当前角色预置的高频页面，优先放在最上方。</span>
                </div>
              </div>
              {quickAccessItems.map((item) => {
                const Icon = navigationIcons[item.icon];
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    className={`nav-item nav-item-quick ${active ? "nav-item-active" : ""}`}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                  >
                    <Icon aria-hidden="true" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </div>
          ) : null}
          {visibleSections.map((section) => {
            const containsActive = section.items.some((item) => item.href === pathname);
            const isCollapsed = containsActive
              ? false
              : (collapsedOverrides[section.key] ?? initialCollapsedSections[section.key] ?? false);
            return (
              <div className={`nav-group${isCollapsed ? " nav-group-collapsed" : ""}`} key={section.key}>
                <button
                  className={`nav-group-header${section.collapsible ? " nav-group-toggle" : ""}`}
                  type="button"
                  onClick={section.collapsible ? () => toggleSection(section.key) : undefined}
                  aria-expanded={!isCollapsed}
                >
                  <div className="nav-section-copy">
                    <span className="nav-section-label">{section.title}</span>
                    <span className="nav-section-description">{section.description}</span>
                  </div>
                  {section.collapsible ? (
                    <span className={`nav-section-toggle${isCollapsed ? " collapsed" : ""}`}>
                      <ChevronDown aria-hidden="true" />
                    </span>
                  ) : null}
                </button>
                {!isCollapsed
                  ? section.items.map((item) => {
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
                    })
                  : null}
              </div>
            );
          })}
          {actor.isAuthenticated && isAdmin ? (
            <div className="nav-group">
              <div className="nav-group-header">
                <div className="nav-section-copy">
                  <span className="nav-section-label">权限治理</span>
                  <span className="nav-section-description">仅管理员使用的账号、角色与 API Key 管理入口。</span>
                </div>
              </div>
              <Link
                className={`nav-item ${pathname === "/security-admin" ? "nav-item-active" : ""}`}
                href="/security-admin"
                onClick={() => setMobileOpen(false)}
              >
                <ShieldCheck aria-hidden="true" />
                <span>权限与安全</span>
              </Link>
            </div>
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
