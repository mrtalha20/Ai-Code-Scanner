import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const isProd = process.env.NODE_ENV === "production";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const res = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Login failed" }));
    return NextResponse.json(err, { status: res.status });
  }

  const data = await res.json();
  const response = NextResponse.json({ success: true });

  // httpOnly cookies — inaccessible to client-side JS, mitigates XSS token theft
  response.cookies.set("access_token", data.access_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "strict",
    maxAge: 60 * 30, // 30 minutes, matches backend JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    path: "/",
  });
  response.cookies.set("refresh_token", data.refresh_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "strict",
    maxAge: 60 * 60 * 24 * 7, // 7 days
    path: "/",
  });

  return response;
}
