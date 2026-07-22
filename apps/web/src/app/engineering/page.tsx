import { redirect } from "next/navigation";
export default function EngineeringRedirectPage() {
  redirect("/process?tab=changes");
}
