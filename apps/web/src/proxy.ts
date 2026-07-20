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

type SessionCheck = "valid" | "invalid" | "unavailable";

function isPublicPath(pathname: string): boolean {
  if (publicPaths.has(pathname)) return true;
  if (pathname.startsWith("/api/")) return false;
  return (
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/favicon") ||
    pathname.match(/\.(?:css|js|map|png|jpg|jpeg|gif|svg|ico|webp|woff2?)$/) !== null
  );
}

/**
 * valid: 会话有效
 * invalid: 明确未登录/令牌失效（401）——可清 cookie
 * unavailable: 后端/数据库暂时不可用（5xx、超时）——保留 cookie，避免误踢登录
 */
async function checkSession(request: NextRequest, token: string): Promise<SessionCheck> {
  const apiUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!apiUrl) return "unavailable";
  try {
    const response = await fetch(`${apiUrl.replace(/\/$/, "")}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
      // 略高于后端 MySQL connect_timeout，减少把慢库误判成未登录
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(5000)]),
    });
    if (response.ok) return "valid";
    if (response.status === 401) return "invalid";
    return "unavailable";
  } catch {
    return "unavailable";
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

function redirectToLogin(request: NextRequest, pathname: string, search: string): NextResponse {
  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(loginUrl);
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
  if (!sessionToken) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json({ error: "请先登录" }, { status: 401 });
    }
    return redirectToLogin(request, pathname, search);
  }

  const sessionStatus = await checkSession(request, sessionToken);
  if (sessionStatus === "valid" || sessionStatus === "unavailable") {
    // unavailable：保留会话 cookie，放行页面；业务 API 仍可能返回 503，但不会误登出
    return NextResponse.next();
  }

  // 仅明确 401 时清 cookie 并踢回登录
  if (pathname.startsWith("/api/")) {
    return clearInvalidSession(NextResponse.json({ error: "请先登录" }, { status: 401 }));
  }
  return clearInvalidSession(redirectToLogin(request, pathname, search));
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|hdri/).*)"],
};
