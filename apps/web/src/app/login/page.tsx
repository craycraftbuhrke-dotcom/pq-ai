"use client";

import { Eye, EyeOff, LoaderCircle, LogIn } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login, loading } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await login(username, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败，请重试");
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="brand-mark" aria-hidden="true">
            PQ
          </div>
          <h1>登录 PQ-AI</h1>
          <p>喷涂工艺与质量智能化闭环系统</p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          {error ? (
            <div className="message-banner message-error">{error}</div>
          ) : null}
          <label className="form-field">
            <span>用户名</span>
            <input
              autoFocus
              required
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="请输入用户名"
            />
          </label>
          <label className="form-field">
            <span>密码</span>
            <div className="password-input-wrap">
              <input
                required
                autoComplete="current-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="请输入密码"
              />
              <button
                type="button"
                className="icon-button"
                aria-label={showPassword ? "隐藏密码" : "显示密码"}
                onClick={() => setShowPassword((value) => !value)}
              >
                {showPassword ? <EyeOff /> : <Eye />}
              </button>
            </div>
          </label>
          <button className="button button-primary auth-submit" type="submit" disabled={loading}>
            {loading ? <LoaderCircle className="spin" /> : <LogIn />}
            {loading ? "登录中..." : "登录"}
          </button>
        </form>
        <div className="auth-footer">
          <span>还没有账号？</span>
          <Link href="/register">注册新账号</Link>
        </div>
      </div>
    </div>
  );
}
