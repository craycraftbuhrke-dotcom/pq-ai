"use client";

import Link from "next/link";
import { ArrowRight, RefreshCcw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useTransition } from "react";

import { navigationIcons } from "@/components/icons";
import { useAuth } from "@/lib/auth-context";
import { domainPortalCards } from "@/lib/ui-data";

export function DomainPortal() {
  const router = useRouter();
  const { actor } = useAuth();
  const [isRefreshing, startTransition] = useTransition();
  const isAdmin = actor.roles.includes("ADMIN") || actor.permissions.includes("*");
  const actorRoles = useMemo(() => new Set(actor.roles), [actor.roles]);

  const cards = useMemo(
    () =>
      domainPortalCards.filter(
        (card) => isAdmin || !card.roles || card.roles.some((role) => actorRoles.has(role)),
      ),
    [actorRoles, isAdmin],
  );

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">工作台</span>
          <h1>各域概览</h1>
          <p>按工艺、材料、质量、主数据、AI 与系统设置进入对应工作台；日常上数从质量管理「批量上传」开始。</p>
        </div>
        <div className="page-actions">
          <button
            className="icon-button icon-button-bordered"
            aria-label={isRefreshing ? "正在刷新" : "刷新"}
            onClick={() => startTransition(() => router.refresh())}
            disabled={isRefreshing}
          >
            <RefreshCcw className={isRefreshing ? "spin" : ""} aria-hidden="true" />
          </button>
        </div>
      </header>

      <section className="domain-portal-grid" aria-label="领域入口">
        {cards.map((card) => {
          const Icon = navigationIcons[card.icon] ?? navigationIcons.dashboard;
          return (
            <article className="domain-portal-card" key={card.key}>
              <div className="domain-portal-card-head">
                <span className="domain-portal-icon">
                  <Icon aria-hidden="true" />
                </span>
                <div>
                  <h2>{card.title}</h2>
                  <p>{card.description}</p>
                </div>
              </div>
              <div className="domain-portal-links">
                {card.links.map((link) => (
                  <Link key={link.href} href={link.href} className="domain-portal-link">
                    {link.label}
                  </Link>
                ))}
              </div>
              <Link className="button button-secondary domain-portal-enter" href={card.href}>
                进入{card.title}
                <ArrowRight aria-hidden="true" />
              </Link>
            </article>
          );
        })}
      </section>
    </div>
  );
}
