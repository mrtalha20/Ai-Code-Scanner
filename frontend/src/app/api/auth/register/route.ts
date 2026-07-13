import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const isProd = process.env.NODE_ENV === "production";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const registerRes = await fetch(`${API_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!registerRes.ok) {
    const err = await registerRes.json().catch(() => ({ detail: "Registration failed" }));
    return NextResponse.json(err, { status: registerRes.status });
  }

  // Auto-login after successful registration
  const loginRes = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!loginRes.ok) {
    // Registered but auto-login failed — still a success for the registration step
    return NextResponse.json({ success: true, autoLogin: false });
  }

  const data = await loginRes.json();
  const response = NextResponse.json({ success: true, autoLogin: true });

  response.cookies.set("access_token", data.access_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "strict",
    maxAge: 60 * 30,
    path: "/",
  });
  response.cookies.set("refresh_token", data.refresh_token, {
    httpOnly: true,
    secure: isProd,
    sameSite: "strict",
    maxAge: 60 * 60 * 24 * 7,
    path: "/",
  });

  return response;
}
