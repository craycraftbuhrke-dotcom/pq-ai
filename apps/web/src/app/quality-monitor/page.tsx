import { redirect } from "next/navigation";

/** Standalone /quality-monitor folds into the quality hub reliability tab. */
export default function QualityMonitorRedirectPage() {
  redirect("/quality?tab=overview");
}
