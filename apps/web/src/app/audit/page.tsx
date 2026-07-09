import { redirect } from "next/navigation";
export default function AuditRedirectPage() {
  redirect("/settings?tab=audit");
}
