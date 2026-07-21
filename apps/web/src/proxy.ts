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

function redirectToLogin(request: NextRequest, pathname: string, search: string): NextResponse {
  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(loginUrl);
}

/**
 * 与常见业务系统一致：代理层只做「有没有会话 cookie」的乐观检查。
 * 不在每次刷新时远程校验 /auth/me，也不在此处清 cookie，避免后端瞬时抖动被误判成登出。
 * 真实鉴权仍由 API Route / 后端中间件执行；明确 401 时由 /api/auth/me 或登出接口清 cookie。
 */
export async function proxy(request: NextRequest) {
  if (!authEnabled) {
    return NextResponse.next();
  }

  const { pathname, search } = request.nextUrl;
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const sessionToken = request.cookies.get(sessionCookieName)?.value ?? "";
  if (sessionToken) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }
  return redirectToLogin(request, pathname, search);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|hdri/).*)"],
};
