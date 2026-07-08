"use client";

import type { ReactNode } from "react";
import { SectionHeader } from "@/components/section-header";

type FilterToolbarProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
};

export function FilterToolbar({
  eyebrow,
  title,
  description,
  actions,
  className,
}: FilterToolbarProps) {
  return (
    <div className={`filter-toolbar${className ? ` ${className}` : ""}`}>
      <SectionHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        titleAs="h2"
        className="filter-toolbar-header"
      />
      {actions ? <div className="filter-toolbar-actions">{actions}</div> : null}
    </div>
  );
}
