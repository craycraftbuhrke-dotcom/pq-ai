import { NextResponse, type NextRequest } from "next/server";

const sessionCookieName = "pq_ai_session";
const publicPaths = new Set([
  "/login",
  "/register",
  "/api/auth/login",
  "/api/auth/register",
  "/api/auth/logout",
  "/icon.svg",
  "/robots.txt",
]);

// 服务端代理默认失败关闭；只有 NODE_ENV=test 的隔离测试可显式关闭。
const authEnabled = !(
  process.env.NODE_ENV === "test" &&
  process.env.AUTH_ENABLED === "false" &&
  process.env.API_AUTH_ENABLED === "false"
);

function isPublicPath(pathname: string): boolean {
  if (publicPaths.has(pathname)) return true;
  if (pathname.startsWith("/api/")) return false;
  return (
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/favicon") ||
    pathname.match(/\.(?:css|js|map|png|jpg|jpeg|gif|svg|ico|webp|woff2?)$/) !== null
  );
}

async function hasValidSession(request: NextRequest, token: string): Promise<boolean> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return false;
  try {
    const response = await fetch(`${apiUrl.replace(/\/$/, "")}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(2500)]),
    });
    return response.ok;
  } catch {
    return false;
  }
}

function clearInvalidSession(response: NextResponse): NextResponse {
  response.cookies.set(sessionCookieName, "", {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 0,
  });
  return response;
}

export async function proxy(request: NextRequest) {
  if (!authEnabled) {
    return NextResponse.next();
  }

  const { pathname, search } = request.nextUrl;
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const sessionToken = request.cookies.get(sessionCookieName)?.value ?? "";
  if (sessionToken && await hasValidSession(request, sessionToken)) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/api/")) {
    return clearInvalidSession(NextResponse.json({ error: "请先登录" }, { status: 401 }));
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("next", `${pathname}${search}`);
  return clearInvalidSession(NextResponse.redirect(loginUrl));
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|hdri/).*)"],
};
