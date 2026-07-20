"use client";

import { KeyRound, LoaderCircle, Save } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/lib/auth-context";
import { roleLabel } from "@/lib/display-labels";

export default function ProfilePage() {
  const router = useRouter();
  const { actor, logout, refreshActor } = useAuth();
  const [displayName, setDisplayName] = useState(actor.displayName);
  const [email, setEmail] = useState("");
  const [department, setDepartment] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const closeNotice = useCallback(() => setNotice(""), []);
  const closeError = useCallback(() => setError(""), []);

  useEffect(() => {
    if (!actor.isAuthenticated) {
      router.push("/login");
    }
  }, [actor.isAuthenticated, router]);

  async function updateProfile(event: FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    setLoading(true);
    try {
      const response = await fetch("/api/auth/me", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          display_name: displayName,
          email: email || null,
          department: department || null,
        }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? "更新失败");
      }
      setNotice("个人信息已更新");
      try {
        await refreshActor();
      } catch {
        setError("个人信息已保存，但页面信息刷新失败，请重新加载页面");
      }
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
      setError("两次输入的新密码不一致");
      return;
    }
    if (newPassword.length < 12) {
      setError("新密码至少 12 位");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch("/api/auth/me/password", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as { error?: string };
        throw new Error(body.error ?? "修改失败");
      }
      setNotice("密码已更新，请使用新密码重新登录");
      setCurrentPassword("");
      setNewPassword("");
      setNewPasswordConfirm("");
      await logout();
      router.push("/login");
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
    <div className="page-stack profile-page">
      {notice ? (
        <button type="button" className="message-banner message-success" onClick={closeNotice}>
          {notice}
        </button>
      ) : null}
      {error ? (
        <button type="button" className="message-banner message-error" onClick={closeError}>
          {error}
        </button>
      ) : null}

      <div className="profile-grid">
        <section className="panel profile-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">基本资料</span>
              <h2>账号信息</h2>
              <p className="section-description">用户名与角色由管理员分配，此处可维护对外显示信息。</p>
            </div>
          </div>
          <form className="profile-form" onSubmit={(event) => void updateProfile(event)}>
            <div className="form-grid">
              <label className="form-field">
                <span>用户名</span>
                <input disabled value={actor.username} className="readonly-input" />
              </label>
              <label className="form-field">
                <span>角色</span>
                <input
                  disabled
                  className="readonly-input"
                  value={
                    actor.roles.length
                      ? actor.roles.map((role) => roleLabel(role)).join(" / ")
                      : "无角色"
                  }
                />
              </label>
              <label className="form-field form-field-wide">
                <span>
                  显示名称<b>*</b>
                </span>
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
            </div>
            <div className="profile-form-actions">
              <button className="button button-primary" type="submit" disabled={loading}>
                {loading ? <LoaderCircle className="spin" /> : <Save />}
                {loading ? "保存中…" : "保存个人信息"}
              </button>
            </div>
          </form>
        </section>

        <section className="panel profile-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">登录安全</span>
              <h2>修改密码</h2>
              <p className="section-description">修改后需使用新密码重新登录。</p>
            </div>
          </div>
          <form className="profile-form" onSubmit={(event) => void changePassword(event)}>
            <div className="form-grid">
              <label className="form-field form-field-wide">
                <span>
                  当前密码<b>*</b>
                </span>
                <input
                  required
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                />
              </label>
              <label className="form-field">
                <span>
                  新密码<b>*</b>
                </span>
                <input
                  required
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder="至少 12 位"
                />
              </label>
              <label className="form-field">
                <span>
                  确认新密码<b>*</b>
                </span>
                <input
                  required
                  type="password"
                  autoComplete="new-password"
                  minLength={12}
                  value={newPasswordConfirm}
                  onChange={(event) => setNewPasswordConfirm(event.target.value)}
                  placeholder="再次输入"
                />
              </label>
            </div>
            <div className="profile-form-actions">
              <button className="button button-primary" type="submit" disabled={loading}>
                {loading ? <LoaderCircle className="spin" /> : <KeyRound />}
                {loading ? "修改中…" : "修改密码"}
              </button>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
