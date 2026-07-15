import { redirect } from "next/navigation";

/** 旧「批量导入测量」入口收敛到质量中心批量上传 Tab。 */
export default function ImportWizardRedirectPage() {
  redirect("/quality?tab=upload");
}
