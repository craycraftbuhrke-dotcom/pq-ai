"use client";

import { X } from "lucide-react";
import { ReactNode, useId } from "react";

import { useModalDismiss } from "@/lib/use-modal-dismiss";

type ModalShellProps = {
  title: ReactNode;
  eyebrow?: ReactNode;
  description?: ReactNode;
  onClose: () => void;
  busy?: boolean;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  focusSelector?: string;
  titleId?: string;
  closeLabel?: string;
};

type ModalBodyProps = {
  children: ReactNode;
  className?: string;
};

type ModalNoteProps = {
  children: ReactNode;
  className?: string;
};

export function ModalShell({
  title,
  eyebrow,
  description,
  onClose,
  busy = false,
  children,
  actions,
  className,
  focusSelector,
  titleId,
  closeLabel = "关闭",
}: ModalShellProps) {
  const generatedTitleId = useId().replace(/:/g, "");
  const headingId = titleId ?? `modal-title-${generatedTitleId}`;
  const descriptionId = description ? `${headingId}-desc` : undefined;

  useModalDismiss({ open: true, onClose, busy, focusSelector });

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}>
      <section
        className={`modal-card modal-shell${className ? ` ${className}` : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        aria-describedby={descriptionId}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-heading">
          <div className="modal-heading-copy">
            {eyebrow ? <span className="modal-eyebrow">{eyebrow}</span> : null}
            <h2 id={headingId}>{title}</h2>
            {description ? (
              <p id={descriptionId} className="modal-description">
                {description}
              </p>
            ) : null}
          </div>
          <button className="icon-button" onClick={onClose} disabled={busy} aria-label={closeLabel}>
            <X aria-hidden="true" />
          </button>
        </div>
        {children}
        {actions ? <div className="modal-actions">{actions}</div> : null}
      </section>
    </div>
  );
}

export function ModalBody({ children, className }: ModalBodyProps) {
  return <div className={`modal-body${className ? ` ${className}` : ""}`}>{children}</div>;
}

export function ModalNote({ children, className }: ModalNoteProps) {
  return <div className={`modal-note${className ? ` ${className}` : ""}`}>{children}</div>;
}
