"use client";

import { Suspense, useCallback, useEffect, useState, type FormEvent } from "react";
import { Key, LoaderCircle, Plus, RefreshCw, Shield, UserPlus, Users, X } from "lucide-react";

import { DomainHub } from "@/components/domain-hub";
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

const ROLE_CATALOG_CODES = [
  "ADMIN",
  "PROCESS_ENGINEER",
  "QUALITY_ENGINEER",
  "APPROVER",
  "ROBOT_OPERATOR",
  "DATA_SCIENTIST",
  "INTEGRATION_OPERATOR",
  "AUDITOR",
];

const TABS = [
  { key: "users", label: "用户管理" },
  { key: "roles", label: "角色管理" },
];

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    ...init,
    headers: init?.headers,
  });
  if (response.status === 204) return undefined as T;
  const payload = (await response.json().catch(() => ({}))) as T & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? `请求失败（${response.status}）`);
  return payload;
}

function SecurityAdminInner() {
  const { actor } = useAuth();
  const [users, setUsers] = useState<UserResource[]>([]);
  const [roles, setRoles] = useState<RoleResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [newUserForm, setNewUserForm] = useState({
    username: "",
    display_name: "",
    password: "",
    email: "",
    department: "",
  });
  const [roleAssignForm, setRoleAssignForm] = useState({
    user_id: "",
    role_code: ROLE_CATALOG_CODES[0],
  });

  const isAdmin =
    actor.isAuthenticated &&
    (actor.permissions.includes("*") || actor.roles.includes("ADMIN"));

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
    if (!isAdmin) return;
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [isAdmin, reload]);

  const closeNotice = useCallback(() => setNotice(""), []);
  const closeError = useCallback(() => setError(""), []);

  async function createUser(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await apiRequest("/api/security/users", {
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
      setNewUserForm({
        username: "",
        display_name: "",
        password: "",
        email: "",
        department: "",
      });
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
          body: JSON.stringify({
            name: `管理签发 ${new Date().toLocaleDateString("zh-CN")}`,
          }),
        },
      );
      setNotice(`系统访问密钥已签发并复制到剪贴板：${result.name}`);
      await navigator.clipboard.writeText(result.raw_key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "签发失败");
    } finally {
      setSubmitting(false);
    }
  }

  if (!isAdmin) {
    return (
      <div className="page-stack">
        <section className="panel">
          <div className="master-empty security-empty">
            <Shield />
            您没有管理用户与角色的权限。请联系管理员。
          </div>
        </section>
      </div>
    );
  }

  return (
    <DomainHub
      title="安全管理"
      tabs={TABS}
      defaultTab="users"
      actions={
        <button
          className="button button-secondary"
          type="button"
          onClick={() => void reload()}
          disabled={loading}
        >
          <RefreshCw className={loading ? "spin" : ""} />
          刷新
        </button>
      }
    >
      {(tab) => (
        <div className="security-hub-body">
          {notice ? (
            <button type="button" className="message-banner message-success" onClick={closeNotice}>
              {notice}
              <X />
            </button>
          ) : null}
          {error ? (
            <button type="button" className="message-banner message-error" onClick={closeError}>
              {error}
              <X />
            </button>
          ) : null}

          {tab === "users" ? (
            <div className="security-grid">
              <section className="security-card">
                <div className="program-subheading compact">
                  <div>
                    <span className="eyebrow">账号开通</span>
                    <h4>新建用户</h4>
                  </div>
                </div>
                <form className="security-form" onSubmit={(event) => void createUser(event)}>
                  <div className="form-grid">
                    <label className="form-field">
                      <span>
                        用户名<b>*</b>
                      </span>
                      <input
                        required
                        pattern="^[A-Za-z0-9_.-]+$"
                        value={newUserForm.username}
                        onChange={(event) =>
                          setNewUserForm({ ...newUserForm, username: event.target.value })
                        }
                        placeholder="英文字母、数字"
                      />
                    </label>
                    <label className="form-field">
                      <span>
                        显示名称<b>*</b>
                      </span>
                      <input
                        required
                        value={newUserForm.display_name}
                        onChange={(event) =>
                          setNewUserForm({ ...newUserForm, display_name: event.target.value })
                        }
                      />
                    </label>
                    <label className="form-field form-field-wide">
                      <span>
                        初始密码<b>*</b>
                      </span>
                      <input
                        required
                        type="password"
                        minLength={12}
                        value={newUserForm.password}
                        onChange={(event) =>
                          setNewUserForm({ ...newUserForm, password: event.target.value })
                        }
                        placeholder="至少 12 位"
                      />
                    </label>
                    <label className="form-field">
                      <span>邮箱</span>
                      <input
                        type="email"
                        value={newUserForm.email}
                        onChange={(event) =>
                          setNewUserForm({ ...newUserForm, email: event.target.value })
                        }
                      />
                    </label>
                    <label className="form-field">
                      <span>部门</span>
                      <input
                        value={newUserForm.department}
                        onChange={(event) =>
                          setNewUserForm({ ...newUserForm, department: event.target.value })
                        }
                      />
                    </label>
                  </div>
                  <div className="security-form-actions">
                    <button className="button button-primary" type="submit" disabled={submitting}>
                      {submitting ? <LoaderCircle className="spin" /> : <UserPlus />}
                      创建用户
                    </button>
                  </div>
                </form>
              </section>

              <section className="security-card">
                <div className="program-subheading compact">
                  <div>
                    <span className="eyebrow">权限</span>
                    <h4>分配角色</h4>
                  </div>
                </div>
                <form className="security-form" onSubmit={(event) => void assignRole(event)}>
                  <div className="form-grid">
                    <label className="form-field form-field-wide">
                      <span>
                        用户<b>*</b>
                      </span>
                      <select
                        required
                        value={roleAssignForm.user_id}
                        onChange={(event) =>
                          setRoleAssignForm({ ...roleAssignForm, user_id: event.target.value })
                        }
                      >
                        <option value="">请选择用户</option>
                        {users.map((user) => (
                          <option key={user.id} value={user.id}>
                            {user.username} / {user.display_name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="form-field form-field-wide">
                      <span>
                        角色<b>*</b>
                      </span>
                      <select
                        value={roleAssignForm.role_code}
                        onChange={(event) =>
                          setRoleAssignForm({ ...roleAssignForm, role_code: event.target.value })
                        }
                      >
                        {ROLE_CATALOG_CODES.map((code) => (
                          <option key={code} value={code}>
                            {ROLE_LABELS[code] ?? code}
                          </option>
                        ))}
                      </select>
                    </label>
                  </div>
                  <div className="security-form-actions">
                    <button
                      className="button button-primary"
                      type="submit"
                      disabled={submitting || !roleAssignForm.user_id}
                    >
                      {submitting ? <LoaderCircle className="spin" /> : <Plus />}
                      分配角色
                    </button>
                  </div>
                </form>
              </section>

              <section className="security-card security-full-span">
                <div className="program-subheading compact">
                  <div>
                    <span className="eyebrow">台账</span>
                    <h4>用户列表</h4>
                    <small>{users.length} 个账号</small>
                  </div>
                </div>
                <div className="master-table-wrap">
                  <table className="master-table">
                    <thead>
                      <tr>
                        <th>用户名</th>
                        <th>显示名称</th>
                        <th>邮箱</th>
                        <th>部门</th>
                        <th>状态</th>
                        <th className="table-actions-cell">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user) => (
                        <tr key={user.id}>
                          <td className="mono">{user.username}</td>
                          <td>{user.display_name}</td>
                          <td>{user.email ?? "—"}</td>
                          <td>{user.department ?? "—"}</td>
                          <td>
                            <span
                              className={`record-status ${user.is_active ? "status-on" : "status-off"}`}
                            >
                              {user.is_active ? "启用" : "停用"}
                            </span>
                          </td>
                          <td className="table-actions-cell">
                            <div className="row-actions">
                              <button
                                className="button button-secondary"
                                type="button"
                                disabled={submitting}
                                onClick={() => void issueApiKey(user.id)}
                              >
                                <Key />
                                签发系统访问密钥
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!users.length && !loading ? (
                    <div className="master-empty">
                      <Users />
                      暂无用户
                    </div>
                  ) : null}
                  {loading ? (
                    <div className="master-empty">
                      <LoaderCircle className="spin" />
                      正在加载用户…
                    </div>
                  ) : null}
                </div>
              </section>
            </div>
          ) : (
            <div className="security-roles">
              <div className="program-subheading compact">
                <div>
                  <span className="eyebrow">权限目录</span>
                  <h4>系统角色</h4>
                  <small>角色权限由后端目录定义，此处只读展示。</small>
                </div>
              </div>
              <div className="master-table-wrap">
                <table className="master-table">
                  <thead>
                    <tr>
                      <th>角色代码</th>
                      <th>名称</th>
                      <th>描述</th>
                      <th>权限</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roles.map((role) => (
                      <tr key={role.id}>
                        <td className="mono">{role.code}</td>
                        <td>{ROLE_LABELS[role.code] ?? role.name}</td>
                        <td>{role.description ?? "—"}</td>
                        <td>
                          <small className="security-perm-list">
                            {(role.permission_codes || []).join(", ") || "—"}
                          </small>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!roles.length && !loading ? (
                  <div className="master-empty">
                    <Shield />
                    暂无角色
                  </div>
                ) : null}
              </div>
            </div>
          )}
        </div>
      )}
    </DomainHub>
  );
}

export default function SecurityAdminPage() {
  return (
    <Suspense
      fallback={
        <div className="page-stack">
          <div className="master-empty">
            <LoaderCircle className="spin" />
            正在加载安全管理…
          </div>
        </div>
      }
    >
      <SecurityAdminInner />
    </Suspense>
  );
}
