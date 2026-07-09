"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";

export type WorkspaceContextValue = {
  factoryId: string;
  modelId: string;
  colorId: string;
  coating: string;
  stage: string;
  setFactoryId: (id: string) => void;
  setModelId: (id: string) => void;
  setColorId: (id: string) => void;
  setCoating: (id: string) => void;
  setStage: (code: string) => void;
  summary: string;
};

const STORAGE_KEY = "pq-ai-workspace-context";

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

type StoredContext = {
  factoryId?: string;
  modelId?: string;
  colorId?: string;
  coating?: string;
  stage?: string;
};

const listeners = new Set<() => void>();

function emitChange() {
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function readStored(): StoredContext {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredContext) : {};
  } catch {
    return {};
  }
}

function writeStored(patch: StoredContext) {
  if (typeof window === "undefined") return;
  const merged = { ...readStored(), ...patch };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
  emitChange();
}

function getSnapshot(): string {
  return window.localStorage.getItem(STORAGE_KEY) ?? "";
}

function getServerSnapshot(): string {
  return "";
}

function parseStored(raw: string): StoredContext {
  if (!raw) return {};
  try {
    return JSON.parse(raw) as StoredContext;
  } catch {
    return {};
  }
}

export function WorkspaceContextProvider({
  children,
  summary,
}: {
  children: ReactNode;
  summary?: string;
}) {
  const raw = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const stored = useMemo(() => parseStored(raw), [raw]);

  const setFactoryId = useCallback((id: string) => writeStored({ factoryId: id }), []);
  const setModelId = useCallback((id: string) => writeStored({ modelId: id }), []);
  const setColorId = useCallback((id: string) => writeStored({ colorId: id }), []);
  const setCoating = useCallback((id: string) => writeStored({ coating: id }), []);
  const setStage = useCallback((code: string) => writeStored({ stage: code }), []);

  const value = useMemo(
    () => ({
      factoryId: stored.factoryId ?? "",
      modelId: stored.modelId ?? "",
      colorId: stored.colorId ?? "",
      coating: stored.coating ?? "basecoat",
      stage: stored.stage ?? "BASECOAT_1",
      setFactoryId,
      setModelId,
      setColorId,
      setCoating,
      setStage,
      summary: summary ?? "",
    }),
    [
      stored.factoryId,
      stored.modelId,
      stored.colorId,
      stored.coating,
      stored.stage,
      setFactoryId,
      setModelId,
      setColorId,
      setCoating,
      setStage,
      summary,
    ],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspaceContext(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    return {
      factoryId: "",
      modelId: "",
      colorId: "",
      coating: "basecoat",
      stage: "BASECOAT_1",
      setFactoryId: () => undefined,
      setModelId: () => undefined,
      setColorId: () => undefined,
      setCoating: () => undefined,
      setStage: () => undefined,
      summary: "",
    };
  }
  return ctx;
}
