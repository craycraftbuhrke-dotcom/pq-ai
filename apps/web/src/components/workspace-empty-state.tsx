"use client";

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

type WorkspaceEmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description?: string;
  compact?: boolean;
  action?: ReactNode;
};

export function WorkspaceEmptyState({
  icon: Icon,
  title,
  description,
  compact = false,
  action,
}: WorkspaceEmptyStateProps) {
  void description;
  return (
    <div className={`workspace-empty-state${compact ? " compact" : ""}`}>
      <div className="workspace-empty-icon">
        <Icon />
      </div>
      <div className="workspace-empty-copy">
        <strong>{title}</strong>
      </div>
      {action ? <div className="workspace-empty-action">{action}</div> : null}
    </div>
  );
}
