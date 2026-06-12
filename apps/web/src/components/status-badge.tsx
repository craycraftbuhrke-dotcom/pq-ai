type StatusBadgeProps = {
  tone: "healthy" | "warning" | "risk" | "info";
  children: React.ReactNode;
};

export function StatusBadge({ tone, children }: StatusBadgeProps) {
  return <span className={`status-badge status-${tone}`}>{children}</span>;
}
