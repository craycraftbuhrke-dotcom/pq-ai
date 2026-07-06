"use client";

import { LoaderCircle, LockKeyhole, ShieldCheck } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

type LoginResult = {
  error?: string;
};

export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = useMemo(() => {
    const candidate = searchParams.get("next");
    return candidate && candidate.startsWith("/") && !candidate.startsWith("//") ? candidate : "/";
  }, [searchParams]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const result = (await response.json().catch(() => ({}))) as LoginResult;
      if (!response.ok) {
        setError(result.error ?? "登录失败，请检查用户名和密码");
        return;
      }
      router.replace(nextPath);
      router.refresh();
    } catch {
      setError("无法连接认证服务");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="login-card" onSubmit={submit}>
      <div className="login-brand">
        <div className="brand-mark">PQ</div>
        <div>
          <span className="eyebrow">Paint Quality AI</span>
          <h1>登录 PQ-AI</h1>
        </div>
      </div>
      <p>
        使用个人账号进入喷涂工艺与质量 AI 闭环系统。API Key 仅保留给 MES、QMS、
        机器人与脚本集成使用。
      </p>
      {error ? <div className="message-banner message-error">{error}</div> : null}
      <label className="form-field">
        <span>用户名</span>
        <input
          autoComplete="username"
          required
          value={username}
          onChange={(event) => setUsername(event.target.value)}
        />
      </label>
      <label className="form-field">
        <span>密码</span>
        <input
          autoComplete="current-password"
          required
          type="password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
      </label>
      <button className="button button-primary login-submit" disabled={submitting}>
        {submitting ? <LoaderCircle className="spin" /> : <LockKeyhole />}
        登录系统
      </button>
      <div className="login-policy">
        <ShieldCheck />
        <span>会话令牌保存为 HttpOnly Cookie，前端脚本不可读取。</span>
      </div>
    </form>
  );
}
