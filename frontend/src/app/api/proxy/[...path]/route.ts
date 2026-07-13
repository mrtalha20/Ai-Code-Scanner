import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, path: string[]) {
  const token = request.cookies.get("access_token")?.value;
  const targetUrl = `${API_URL}/api/v1/${path.join("/")}${request.nextUrl.search}`;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const init: RequestInit = { method: request.method, headers };
  if (!["GET", "HEAD"].includes(request.method)) {
    const body = await request.text();
    if (body) init.body = body;
  }

  const res = await fetch(targetUrl, init);
  const data = await res.text();

  // If access token expired, attempt one silent refresh + retry
  if (res.status === 401 && request.cookies.get("refresh_token")?.value) {
    const refreshRes = await fetch(`${request.nextUrl.origin}/api/auth/refresh`, {
      method: "POST",
      headers: { Cookie: request.headers.get("cookie") ?? "" },
    });
    if (refreshRes.ok) {
      const newToken = refreshRes.headers
        .getSetCookie?.()
        .find((c) => c.startsWith("access_token="))
        ?.split(";")[0]
        ?.split("=")[1];
      if (newToken) {
        const retryHeaders = { ...headers, Authorization: `Bearer ${newToken}` };
        const retryRes = await fetch(targetUrl, { ...init, headers: retryHeaders });
        const retryData = await retryRes.text();
        const response = new NextResponse(retryData, {
          status: retryRes.status,
          headers: { "Content-Type": retryRes.headers.get("Content-Type") ?? "application/json" },
        });
        refreshRes.headers.getSetCookie?.().forEach((c) => response.headers.append("Set-Cookie", c));
        return response;
      }
    }
  }

  return new NextResponse(data, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("Content-Type") ?? "application/json" },
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}
export async function POST(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}
export async function PUT(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}
export async function DELETE(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  return proxy(request, path);
}
