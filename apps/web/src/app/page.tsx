import { Dashboard } from "@/components/dashboard";
import { getDashboardSnapshot } from "@/lib/dashboard-data";

export default async function Home() {
  const snapshot = await getDashboardSnapshot();
  return <Dashboard snapshot={snapshot} />;
}
