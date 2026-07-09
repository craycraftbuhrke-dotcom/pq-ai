"use client";

import type { ReactNode } from "react";

type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  badge?: ReactNode;
  actions?: ReactNode;
  className?: string;
  compact?: boolean;
  titleAs?: "h1" | "h2" | "h3";
};

export function SectionHeader({
  eyebrow,
  title,
  description,
  badge,
  actions,
  className,
  compact = false,
  titleAs = "h2",
}: SectionHeaderProps) {
  const TitleTag = titleAs;
  const rootClassName = `section-header${compact ? " compact" : ""}${className ? ` ${className}` : ""}`;

  return (
    <div className={rootClassName}>
      <div className="section-header-copy">
        {eyebrow ? <span className="section-eyebrow">{eyebrow}</span> : null}
        <TitleTag>{title}</TitleTag>
        {description ? <p className="section-description">{description}</p> : null}
      </div>
      {badge ? <div className="section-header-badge">{badge}</div> : null}
      {actions ? <div className="section-header-actions">{actions}</div> : null}
    </div>
  );
}
