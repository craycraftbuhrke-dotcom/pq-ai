"use client";

import { KeyRound, LoaderCircle, Save } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/lib/auth-context";

export default function ProfilePage() {
  const router = useRouter();
  const { actor, setApiKey } = useAuth();
  const [displayName, setDisplayName] = useState(actor.displayName);
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!actor.isAuthenticated) {
      router.push("/login");
    }
  }, [actor.isAuthenticated, router]);

  function getApiKey(): string {
    const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  async function updateProfile(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    setLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    try {
      const response = await fetch(`${apiUrl}/auth/me`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": getApiKey(),
        },
        body: JSON.stringify({ display_name: displayName, email: email || null, department: department || null }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail ?? "更新失败");
      }
      const data = (await response.json()) as { display_name: string };
      setNotice("个人信息已更新");
      if (data.display_name) setApiKey(getApiKey());
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新失败");
    } finally {
      setLoading(false);
    }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (newPassword !== newPasswordConfirm) {
      setError("两次输入的密码不一致");
      return;
    }
    if (newPassword.length < 6) {
      setError("新密码至少 6 位");
      return;
    }
    setLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    try {
      const response = await fetch(`${apiUrl}/auth/me/password`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": getApiKey(),
        },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { detail?: string };
        throw new Error(body.detail ?? "修改失败");
      }
      setNotice("密码已更新，请使用新密码重新登录");
      setCurrentPassword("");
      setNewPassword("");
      setNewPasswordConfirm("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "密码修改失败");
    } finally {
      setLoading(false);
    }
  }

  if (!actor.isAuthenticated) {
    return null;
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">个人中心</span>
          <h1>个人中心</h1>
          <p>管理您的个人信息与安全设置。</p>
        </div>
      </header>
      {notice ? (
        <button className="message-banner message-success" onClick={() => setNotice("")}>
          {notice}
        </button>
      ) : null}
      {error ? (
        <button className="message-banner message-error" onClick={() => setError("")}>
          {error}
        </button>
      ) : null}
      <div className="profile-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">账号信息</span>
              <h2>账号信息</h2>
            </div>
          </div>
          <form className="auth-form" onSubmit={updateProfile}>
            <label className="form-field">
              <span>用户名</span>
              <input disabled value={actor.username} />
            </label>
            <label className="form-field">
              <span>显示名称</span>
              <input
                required
                value={displayName}
                onChange={(event) => setDisplayName(event.target.value)}
              />
            </label>
            <label className="form-field">
              <span>邮箱</span>
              <input
                type="email"
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
            <label className="form-field">
              <span>角色</span>
              <input
                disabled
                value={actor.roles.length ? actor.roles.join(" / ") : "无角色"}
                className="readonly-input"
              />
            </label>
            <button className="button button-primary" type="submit" disabled={loading}>
              {loading ? <LoaderCircle className="spin" /> : <Save />}
              {loading ? "保存中..." : "保存个人信息"}
            </button>
          </form>
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">登录安全</span>
              <h2>修改密码</h2>
            </div>
          </div>
          <form className="auth-form" onSubmit={changePassword}>
            <label className="form-field">
              <span>当前密码</span>
              <input
                required
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
              />
            </label>
            <label className="form-field">
              <span>新密码</span>
              <input
                required
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                placeholder="至少 6 位"
                minLength={6}
              />
            </label>
            <label className="form-field">
              <span>确认新密码</span>
              <input
                required
                type="password"
                autoComplete="new-password"
                value={newPasswordConfirm}
                onChange={(event) => setNewPasswordConfirm(event.target.value)}
                placeholder="再次输入新密码"
                minLength={6}
              />
            </label>
            <button className="button button-primary" type="submit" disabled={loading}>
              {loading ? <LoaderCircle className="spin" /> : <KeyRound />}
              {loading ? "修改中..." : "修改密码"}
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
