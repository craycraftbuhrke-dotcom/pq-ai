import "server-only";

import { randomUUID } from "crypto";
import { mkdir, open, rm, rmdir, stat, type FileHandle } from "fs/promises";
import path from "path";

const LOCK_WAIT_MS = 30_000;
const LOCK_HEARTBEAT_MS = 5_000;

function sleep(milliseconds: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

type RuntimeFileLockOptions = {
  waitMs?: number;
};

function ownerPath(lockPath: string, token: string): string {
  return path.join(/*turbopackIgnore: true*/ lockPath, `${token}.owner.json`);
}

async function legacyRecoveryExists(lockPath: string): Promise<boolean> {
  return stat(`${lockPath}.recovery`).then(() => true).catch(() => false);
}

async function releaseOwnedLock(lockPath: string, token: string): Promise<void> {
  // A replaced lock has a different owner filename, so a late releaser cannot
  // remove the replacement owner's file or its non-empty lock directory.
  await rm(ownerPath(lockPath, token), { force: true }).catch(() => undefined);
  await rmdir(lockPath).catch((error) => {
    if (
      !["ENOENT", "ENOTDIR", "ENOTEMPTY", "EEXIST"].includes(
        (error as NodeJS.ErrnoException).code ?? "",
      )
    ) {
      throw error;
    }
  });
}

async function waitForLock(deadline: number): Promise<void> {
  if (Date.now() >= deadline) {
    throw Object.assign(
      new Error("资源锁仍被占用；如确认相关服务已停止，请由运维清理孤儿锁后重试"),
      { status: 409 },
    );
  }
  await sleep(50 + Math.floor(Math.random() * 100));
}

export async function withRuntimeFileLock<T>(
  lockPath: string,
  operation: () => Promise<T>,
  options: RuntimeFileLockOptions = {},
): Promise<T> {
  await mkdir(path.dirname(lockPath), { recursive: true });
  const deadline = Date.now() + Math.max(0, options.waitMs ?? LOCK_WAIT_MS);
  const token = randomUUID();
  let ownerHandle: FileHandle | null = null;

  while (!ownerHandle) {
    if (await legacyRecoveryExists(lockPath)) {
      await waitForLock(deadline);
      continue;
    }
    try {
      await mkdir(lockPath);
      try {
        ownerHandle = await open(ownerPath(lockPath, token), "wx");
        await ownerHandle.writeFile(
          `${JSON.stringify({ token, createdAt: Date.now(), pid: process.pid })}\n`,
          "utf-8",
        );
        await ownerHandle.sync();
      } catch (error) {
        await ownerHandle?.close().catch(() => undefined);
        ownerHandle = null;
        await releaseOwnedLock(lockPath, token);
        throw error;
      }
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
      await waitForLock(deadline);
    }
  }

  let heartbeatError: unknown = null;
  let heartbeatInFlight = Promise.resolve();
  let operationCompleted = false;
  const heartbeat = setInterval(() => {
    heartbeatInFlight = heartbeatInFlight
      .then(async () => {
        if (!ownerHandle) return;
        const now = new Date();
        await ownerHandle.utimes(now, now);
      })
      .catch((error) => {
        if (!operationCompleted) heartbeatError ??= error;
      });
  }, LOCK_HEARTBEAT_MS);
  heartbeat.unref();

  try {
    const result = await operation();
    operationCompleted = true;
    clearInterval(heartbeat);
    await heartbeatInFlight;
    if (heartbeatError) {
      throw Object.assign(new Error("资源锁租约续期失败，本次结果不能确认"), { status: 409 });
    }
    return result;
  } finally {
    clearInterval(heartbeat);
    await heartbeatInFlight;
    await ownerHandle.close().catch(() => undefined);
    ownerHandle = null;
    await releaseOwnedLock(lockPath, token);
  }
}
