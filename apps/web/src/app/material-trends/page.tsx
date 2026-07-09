﻿import { redirect } from "next/navigation";
export default function MaterialTrendsRedirectPage() {
  redirect("/materials?tab=overview");
}
