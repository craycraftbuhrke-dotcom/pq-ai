import { redirect } from "next/navigation";

/** Legacy /quality-monitor folds into quality hub measurements. */
export default function QualityMonitorRedirectPage() {
  redirect("/quality?tab=measurements");
}
