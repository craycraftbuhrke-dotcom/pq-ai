import { redirect } from "next/navigation";

export default function ProductionRedirectPage() {
  redirect("/process?tab=runs");
}
