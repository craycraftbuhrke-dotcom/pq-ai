import { NextResponse, type NextRequest } from "next/server";

const sessionCookieName = "pq_ai_session";
const publicPaths = new Set([
  "/login",
  "/register",
  "/api/auth/login",
  "/api/auth/logout",
  "/icon.svg",
  "/robots.txt",
]);

// 认证总开关：与后端 API_AUTH_ENABLED 保持一致。默认 false（测试期直接进入系统）。
// 未来测试通过后：设置环境变量 NEXT_PUBLIC_AUTH_ENABLED=true 恢复完整登录流程。
const authEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

function isPublicPath(pathname: string): boolean {
  return (
    publicPaths.has(pathname) ||
    pathname.startsWith("/_next/") ||
    pathname.startsWith("/favicon") ||
    pathname.match(/\\.(?:css|js|map|png|jpg|jpeg|gif|svg|ico|webp|woff2?)$/) !== null
  );
}

export function middleware(request: NextRequest) {
  // 认证关闭：所有请求一律放行，不走登录墙。
  if (!authEnabled) {
    return NextResponse.next();
  }

  const { pathname, search } = request.nextUrl;
  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  const hasSession = Boolean(request.cookies.get(sessionCookieName)?.value);
  const hasApiKey = Boolean(request.cookies.get("pq_api_key")?.value);
  if (hasSession || hasApiKey) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "请先登录" }, { status: 401 });
  }

  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("next", `${pathname}${search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image).*)"],
};
