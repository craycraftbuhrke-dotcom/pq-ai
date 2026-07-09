"use client";

import { Key, LoaderCircle, Plus, RefreshCw, Shield, UserPlus, Users, X } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useAuth } from "@/lib/auth-context";
import { ROLE_LABELS } from "@/lib/display-labels";

type UserResource = {
  id: string;
  username: string;
  display_name: string;
  email: string | null;
  department: string | null;
  is_active: boolean;
  created_at: string;
};

type RoleResource = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  permission_codes: string[];
};

type Tab = "users" | "roles" | "api-keys";

const ROLE_CATALOG_CODES = [
  "ADMIN", "PROCESS_ENGINEER", "QUALITY_ENGINEER",
  "APPROVER", "ROBOT_OPERATOR", "DATA_SCIENTIST",
  "INTEGRATION_OPERATOR", "AUDITOR",
];

function getApiKeyFromCookie(): string {
  const match = document.cookie.match(/(?:^|;\s*)pq_api_key=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    headers: { ...init?.headers, "x-api-key": getApiKeyFromCookie() },
    ...init,
  });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? `请求失败（${response.status}）`);
  return payload;
}

export default function SecurityAdminPage() {
  const { actor } = useAuth();
  const [tab, setTab] = useState<Tab>("users");
  const [users, setUsers] = useState<UserResource[]>([]);
  const [roles, setRoles] = useState<RoleResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const [newUserForm, setNewUserForm] = useState({ username: "", display_name: "", password: "", email: "", department: "" });
  const [roleAssignForm, setRoleAssignForm] = useState({ user_id: "", role_code: ROLE_CATALOG_CODES[0] });

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextUsers, nextRoles] = await Promise.all([
        apiRequest<UserResource[]>("/api/security/users"),
        apiRequest<RoleResource[]>("/api/security/roles"),
      ]);
      setUsers(nextUsers);
      setRoles(nextRoles);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  if (!actor.isAuthenticated || !actor.permissions.includes("*") && !actor.roles.includes("ADMIN")) {
    return (
      <div className="page-stack">
        <header className="page-header">
          <div>
            <span className="page-kicker">账号安全</span>
            <h1>安全管理</h1>
            <p>需要管理员权限才能访问此页面。</p>
          </div>
        </header>
        <div className="master-empty">
          <Shield /> 您没有管理用户与角色的权限。请联系管理员。
        </div>
      </div>
    );
  }

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiRequest("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: newUserForm.username,
          password: newUserForm.password,
          display_name: newUserForm.display_name,
          email: newUserForm.email || null,
          department: newUserForm.department || null,
        }),
      });
      setNotice("用户已创建");
      setNewUserForm({ username: "", display_name: "", password: "", email: "", department: "" });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function assignRole(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiRequest(`/api/security/users/${roleAssignForm.user_id}/roles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role_code: roleAssignForm.role_code }),
      });
      setNotice("角色已分配");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "分配失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function issueApiKey(userId: string) {
    setSubmitting(true);
    setError("");
    try {
      const result = await apiRequest<{ raw_key: string; id: string; name: string }>(
        `/api/security/users/${userId}/api-keys`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: `管理签发 ${new Date().toLocaleDateString("zh-CN")}` }),
        },
      );
      setNotice(`API Key 已签发并复制到剪贴板：${result.name}`);
      await navigator.clipboard.writeText(result.raw_key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "签发失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <span className="page-kicker">用户与角色</span>
          <h1>安全管理</h1>
          <p>用户管理、角色分配与 API Key 签发。</p>
        </div>
        <button className="button button-secondary" onClick={() => void reload()} disabled={loading}>
          <RefreshCw className={loading ? "spin" : ""} /> 刷新
        </button>
      </header>
      {notice ? <button className="message-banner message-success" onClick={() => setNotice("")}>{notice}<X /></button> : null}
      {error ? <button className="message-banner message-error" onClick={() => setError("")}>{error}<X /></button> : null}
      <div className="master-tabs" role="tablist">
        <button className={tab === "users" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("users")}>
          <Users /> 用户管理 <span>{users.length}</span>
        </button>
        <button className={tab === "roles" ? "master-tab master-tab-active" : "master-tab"} onClick={() => setTab("roles")}>
          <Shield /> 角色管理 <span>{roles.length}</span>
        </button>
      </div>
      {tab === "users" ? (
        <div className="security-grid">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">新建用户</span>
                <h2>新建用户</h2>
              </div>
            </div>
            <form className="auth-form" onSubmit={createUser}>
              <label className="form-field"><span>用户名 <b>*</b></span><input required pattern="^[A-Za-z0-9_.-]+$" value={newUserForm.username} onChange={(e) => setNewUserForm({ ...newUserForm, username: e.target.value })} placeholder="英文字母、数字" /></label>
              <label className="form-field"><span>显示名称 <b>*</b></span><input required value={newUserForm.display_name} onChange={(e) => setNewUserForm({ ...newUserForm, display_name: e.target.value })} /></label>
              <label className="form-field"><span>密码 <b>*</b></span><input required type="password" value={newUserForm.password} onChange={(e) => setNewUserForm({ ...newUserForm, password: e.target.value })} placeholder="至少 6 位" minLength={6} /></label>
              <label className="form-field"><span>邮箱</span><input type="email" value={newUserForm.email} onChange={(e) => setNewUserForm({ ...newUserForm, email: e.target.value })} /></label>
              <label className="form-field"><span>部门</span><input value={newUserForm.department} onChange={(e) => setNewUserForm({ ...newUserForm, department: e.target.value })} /></label>
              <button className="button button-primary" type="submit" disabled={submitting}>{submitting ? <LoaderCircle className="spin" /> : <UserPlus />}创建用户</button>
            </form>
          </section>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">分配角色</span>
                <h2>分配角色</h2>
              </div>
            </div>
            <form className="auth-form" onSubmit={assignRole}>
              <label className="form-field"><span>用户</span>
                <select value={roleAssignForm.user_id} onChange={(e) => setRoleAssignForm({ ...roleAssignForm, user_id: e.target.value })}>
                  <option value="">请选择</option>
                  {users.map((u) => <option key={u.id} value={u.id}>{u.username} / {u.display_name}</option>)}
                </select>
              </label>
              <label className="form-field"><span>角色</span>
                <select value={roleAssignForm.role_code} onChange={(e) => setRoleAssignForm({ ...roleAssignForm, role_code: e.target.value })}>
                  {ROLE_CATALOG_CODES.map((code) => <option key={code} value={code}>{ROLE_LABELS[code] ?? code}</option>)}
                </select>
              </label>
              <button className="button button-primary" type="submit" disabled={submitting || !roleAssignForm.user_id}>{submitting ? <LoaderCircle className="spin" /> : <Plus />}分配</button>
            </form>
          </section>
          <section className="panel security-full-span">
            <div className="panel-heading">
              <div>
                <span className="eyebrow">用户列表</span>
                <h2>用户列表</h2>
              </div>
            </div>
            <div className="master-table-wrap">
              <table className="master-table">
                <thead><tr><th>用户名</th><th>显示名称</th><th>邮箱</th><th>部门</th><th>状态</th><th className="table-actions-cell">操作</th></tr></thead>
                <tbody>
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td className="mono">{user.username}</td>
                      <td>{user.display_name}</td>
                      <td>{user.email ?? "—"}</td>
                      <td>{user.department ?? "—"}</td>
                      <td><span className={`record-status ${user.is_active ? "status-on" : "status-off"}`}>{user.is_active ? "启用" : "停用"}</span></td>
                      <td className="table-actions-cell">
                        <div className="row-actions">
                          <button className="button button-secondary" onClick={() => void issueApiKey(user.id)}>
                            <Key />
                            签发 API Key
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!users.length ? <div className="master-empty"><Users /> 暂无用户</div> : null}
            </div>
          </section>
        </div>
      ) : (
        <section className="panel">
          <div className="master-table-wrap">
            <table className="master-table">
              <thead><tr><th>角色代码</th><th>名称</th><th>描述</th><th>权限</th></tr></thead>
              <tbody>
                {roles.map((role) => (
                  <tr key={role.id}>
                    <td className="mono">{role.code}</td>
                    <td>{role.name}</td>
                    <td>{role.description ?? "—"}</td>
                    <td><small>{(role.permission_codes || []).join(", ")}</small></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!roles.length ? <div className="master-empty"><Shield /> 暂无角色</div> : null}
          </div>
        </section>
      )}
    </div>
  );
}
