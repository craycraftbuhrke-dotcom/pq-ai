import { getAuditPageData } from "@/lib/business-data";
import { SettingsHubClient } from "./settings-hub-client";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const audit = await getAuditPageData();
  return (
    <SettingsHubClient
      audit={{
        stats: audit.stats,
        columns: ["请求 ID", "操作人", "权限动作", "接口路径", "状态码", "发生时间"],
        rows: audit.rows,
        source: audit.source,
      }}
    />
  );
}
