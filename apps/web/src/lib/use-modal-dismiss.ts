"use client";

import { useEffect, useRef } from "react";

/**
 * Shared modal dismiss + initial-focus behavior.
 *
 * - Esc closes when open and not busy
 * - Focus the first form field once when the modal opens (not on every parent re-render)
 * - Restore focus to the previously focused element on close
 *
 * Important: do NOT put `onClose` / `busy` in the focus effect deps. Unstable inline
 * `onClose` handlers used to re-run this effect on every keystroke and steal focus
 * to the header close button (first matching `button` in DOM order).
 */
const DEFAULT_FOCUS_SELECTOR =
  "input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled])";

export function useModalDismiss(options: {
  open: boolean;
  onClose: () => void;
  busy?: boolean;
  /** First focusable locator inside `.modal-card`. Defaults to form fields only. */
  focusSelector?: string;
}) {
  const { open, onClose, busy = false, focusSelector } = options;
  const onCloseRef = useRef(onClose);
  const busyRef = useRef(busy);
  const focusSelectorRef = useRef(focusSelector);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  onCloseRef.current = onClose;
  busyRef.current = busy;
  focusSelectorRef.current = focusSelector;

  useEffect(() => {
    if (!open) return;
    if (typeof document === "undefined") return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (busyRef.current) return;
      event.stopPropagation();
      onCloseRef.current();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (typeof document === "undefined") return;

    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;

    const focusTimer = window.setTimeout(() => {
      const container = document.querySelector(".modal-card");
      if (!container) return;

      const selector = focusSelectorRef.current ?? DEFAULT_FOCUS_SELECTOR;
      let target = container.querySelector<HTMLElement>(selector);

      if (!target) {
        const buttons = Array.from(
          container.querySelectorAll<HTMLElement>("button:not([disabled])"),
        );
        target =
          buttons.find(
            (button) =>
              !button.closest(".modal-heading") &&
              button.getAttribute("data-modal-close") == null,
          ) ?? null;
      }

      target?.focus();
    }, 0);

    return () => {
      window.clearTimeout(focusTimer);
      const previouslyFocused = previouslyFocusedRef.current;
      if (
        previouslyFocused &&
        typeof previouslyFocused.focus === "function" &&
        document.contains(previouslyFocused)
      ) {
        previouslyFocused.focus();
      }
    };
  }, [open]);
}
