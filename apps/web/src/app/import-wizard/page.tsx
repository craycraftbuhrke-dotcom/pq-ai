import { redirect } from "next/navigation";

/** 旧「批量导入测量」入口收敛到质量数据中心（默认批量上传 Tab）。 */
export default function ImportWizardRedirectPage() {
  redirect("/quality");
}
