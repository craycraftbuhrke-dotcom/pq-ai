"use client";

import { useEffect, useState } from "react";

type SystemState = {
  status: "checking" | "ready" | "not_ready" | "unavailable";
  message: string;
};

const checkingState: SystemState = {
  status: "checking",
  message: "正在检查系统和数据连接",
};

export function SystemStatus() {
  const [state, setState] = useState<SystemState>(checkingState);

  useEffect(() => {
    let cancelled = false;
    let activeRequest: AbortController | null = null;

    async function refresh() {
      activeRequest?.abort();
      const controller = new AbortController();
      activeRequest = controller;
      const next = await fetch("/api/health", {
        cache: "no-store",
        signal: controller.signal,
      })
        .then((response) => response.json() as Promise<SystemState>)
        .catch((error) =>
          error instanceof DOMException && error.name === "AbortError"
            ? null
            : { status: "unavailable" as const, message: "系统状态检查失败" },
        );
      if (!cancelled && activeRequest === controller && next) setState(next);
    }

    const firstCheck = window.setTimeout(() => void refresh(), 0);
    const interval = window.setInterval(() => void refresh(), 30_000);
    return () => {
      cancelled = true;
      activeRequest?.abort();
      window.clearTimeout(firstCheck);
      window.clearInterval(interval);
    };
  }, []);

  const title =
    state.status === "ready"
      ? "系统可用"
      : state.status === "checking"
        ? "正在检查"
        : state.status === "not_ready"
          ? "数据连接未就绪"
          : "系统服务不可用";

  return (
    <div className={`system-state system-state-${state.status}`} title={state.message}>
      <span className="live-dot" />
      <div>
        <strong>{title}</strong>
        <span>{state.message}</span>
      </div>
    </div>
  );
}
