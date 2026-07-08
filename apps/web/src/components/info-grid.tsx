"use client";

import type { ReactNode } from "react";

type InfoGridItem = {
  label: string;
  value: ReactNode;
};

type InfoGridProps = {
  items: InfoGridItem[];
  className?: string;
};

export function InfoGrid({ items, className }: InfoGridProps) {
  return (
    <div className={`info-grid${className ? ` ${className}` : ""}`}>
      {items.map((item) => (
        <div className="info-grid-item" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}
