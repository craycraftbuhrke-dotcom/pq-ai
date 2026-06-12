import { ModulePage } from "@/components/module-page";
import { getAuditPageData } from "@/lib/business-data";

export default async function AuditPage() {
  const data = await getAuditPageData();
  return (
    <ModulePage
      kicker="身份、权限与操作追溯"
      title="审计中心"
      description="追踪关键写操作、授权拒绝、请求身份、资源对象与执行结果。"
      primaryAction="导出审计记录"
      stats={data.stats}
      columns={["请求 ID", "操作人", "权限动作", "接口路径", "状态码", "发生时间"]}
      rows={data.rows}
      source={data.source}
    />
  );
}
