import { redirect } from "next/navigation";

export default function ProgramsRedirectPage() {
  redirect("/process?tab=recipes");
}
