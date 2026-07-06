"use client";

import { useEffect } from "react";

/**
 * P0 无障碍增强：所有 modal 复用这一个 hook，避免每处手写监听器。
 *
 * 提供三件事：
 *  1) Esc 键触发 onClose（仅 open=true 且 !busy 才生效——保存中禁止意外关闭）
 *  2) modal 挂载后自动 focus 第一个可交互控件
 *  3) 关闭后归还焦点到打开前的 activeElement，保持键盘导航连续
 *
 * 采用“单实例假设”：全站同时只允许一个 modal 打开，通过 document.querySelector 定位当前 modal。
 * 不引入 focus-trap 等三方依赖；完整 focus trap 会随 P1 阶段的 <Modal> 基础组件一并引入。
 */
export function useModalDismiss(options: {
  open: boolean;
  onClose: () => void;
  busy?: boolean;
  /** 首个可 focus 元素的定位器；默认 `.modal-card` 里首个 input/select/textarea/button。 */
  focusSelector?: string;
}) {
  const { open, onClose, busy = false, focusSelector } = options;

  useEffect(() => {
    if (!open) return;
    if (typeof document === "undefined") return;

    const previouslyFocused = document.activeElement as HTMLElement | null;

    // 首字段 focus：在下一帧执行，避免与 React 挂载时的默认 focus 竞争。
    const focusTimer = window.setTimeout(() => {
      const container = document.querySelector(".modal-card");
      if (!container) return;
      const selector =
        focusSelector ??
        "input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])";
      const target = container.querySelector<HTMLElement>(selector);
      target?.focus();
    }, 0);

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (busy) return; // 保存中禁止 Esc 关闭，避免丢失表单内容
      event.stopPropagation();
      onClose();
    }

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      window.clearTimeout(focusTimer);
      document.removeEventListener("keydown", handleKeyDown);
      if (
        previouslyFocused &&
        typeof previouslyFocused.focus === "function" &&
        document.contains(previouslyFocused)
      ) {
        previouslyFocused.focus();
      }
    };
  }, [open, busy, onClose, focusSelector]);
}
