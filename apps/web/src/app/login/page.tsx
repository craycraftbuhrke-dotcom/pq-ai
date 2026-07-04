import { Suspense } from "react";

import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <main className="login-page">
      <section className="login-hero">
        <span className="page-kicker">AUTHENTICATION · RBAC · AUDIT</span>
        <h2>喷涂工艺与质量智能闭环系统</h2>
        <p>
          登录后按角色权限访问主数据、喷涂程序、生产实绩、质量数据、AI 建模、
          集成任务和审计中心。所有写操作继续进入审计日志。
        </p>
        <div className="login-feature-grid">
          <article>
            <strong>个人账号</strong>
            <span>用户、角色、权限与登录会话独立管理。</span>
          </article>
          <article>
            <strong>权限控制</strong>
            <span>沿用后端 RBAC，写操作按业务权限校验。</span>
          </article>
          <article>
            <strong>安全审计</strong>
            <span>登录后的业务变更保留请求、操作者和状态码。</span>
          </article>
        </div>
      </section>
      <Suspense>
        <LoginForm />
      </Suspense>
    </main>
  );
}
