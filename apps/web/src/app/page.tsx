import { Dashboard } from "@/components/dashboard";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

// 禁用构建时静态化：dashboard 在 SSR 中读取 process.env.API_URL 拉取实时数据，
// 若被 next build 阶段预渲染，构建容器里没有 API_URL，会把"未配置"错误消息固化进 HTML。
export const dynamic = "force-dynamic";

export default async function Home() {
  const snapshot = await getDashboardSnapshot();
  return <Dashboard snapshot={snapshot} />;
}
