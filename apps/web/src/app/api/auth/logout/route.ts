import { NextResponse } from "next/server";

import { apiRequestHeaders, sessionCookieName } from "@/lib/auth-data";

export async function POST(request: Request) {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (apiUrl) {
    await fetch(`${apiUrl}/auth/logout`, {
      method: "POST",
      headers: await apiRequestHeaders(request),
      cache: "no-store",
    }).catch(() => undefined);
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(sessionCookieName, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
  return response;
}
