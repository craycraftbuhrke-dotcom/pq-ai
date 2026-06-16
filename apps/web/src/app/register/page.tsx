"use client";

import { LoaderCircle, UserPlus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { useAuth } from "@/lib/auth-context";

export default function RegisterPage() {
  const router = useRouter();
  const { register, loading } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (password !== passwordConfirm) {
      setError("两次输入的密码不一致");
      return;
    }
    if (password.length < 6) {
      setError("密码长度至少 6 位");
      return;
    }
    try {
      await register(username, password, displayName, email, department);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败，请重试");
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="brand-mark" aria-hidden="true">
            PQ
          </div>
          <h1>注册 PQ-AI</h1>
          <p>创建您的喷涂工艺管理账号</p>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          {error ? (
            <div className="message-banner message-error">{error}</div>
          ) : null}
          <label className="form-field">
            <span>
              用户名 <b>*</b>
            </span>
            <input
              autoFocus
              required
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="英文字母、数字、下划线"
              pattern="^[A-Za-z0-9_.-]+$"
            />
          </label>
          <label className="form-field">
            <span>
              显示名称 <b>*</b>
            </span>
            <input
              required
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="例如：陈工"
            />
          </label>
          <label className="form-field">
            <span>
              密码 <b>*</b>
            </span>
            <input
              required
              autoComplete="new-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="至少 6 位"
              minLength={6}
            />
          </label>
          <label className="form-field">
            <span>
              确认密码 <b>*</b>
            </span>
            <input
              required
              autoComplete="new-password"
              type="password"
              value={passwordConfirm}
              onChange={(event) => setPasswordConfirm(event.target.value)}
              placeholder="再次输入密码"
              minLength={6}
            />
          </label>
          <label className="form-field">
            <span>邮箱</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="选填"
            />
          </label>
          <label className="form-field">
            <span>部门</span>
            <input
              value={department}
              onChange={(event) => setDepartment(event.target.value)}
              placeholder="选填"
            />
          </label>
          <button className="button button-primary auth-submit" type="submit" disabled={loading}>
            {loading ? <LoaderCircle className="spin" /> : <UserPlus />}
            {loading ? "注册中..." : "注册"}
          </button>
        </form>
        <div className="auth-footer">
          <span>已有账号？</span>
          <Link href="/login">返回登录</Link>
        </div>
      </div>
    </div>
  );
}
