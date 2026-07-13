/**
 * All requests go through Next.js API routes (/api/auth/*, /api/proxy/*)
 * which hold the JWT in an httpOnly cookie. The browser never sees the token,
 * eliminating XSS-based token theft. See src/app/api/ for the route handlers.
 */

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api/proxy${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const api = {
  register: async (email: string, password: string) => {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(err.detail ?? "Registration failed");
    }
    return res.json();
  },

  login: async (email: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(err.detail ?? "Invalid email or password");
    }
    return res.json();
  },

  logout: async () => {
    await fetch("/api/auth/logout", { method: "POST" });
  },

  createScan: (body: { code?: string; language?: string; repo_url?: string }) =>
    request("/scans", { method: "POST", body: JSON.stringify(body) }),

  getScan: (id: string) => request(`/scans/${id}`),

  listScans: (skip = 0, limit = 20) => request(`/scans?skip=${skip}&limit=${limit}`),

  deleteScan: (id: string) => request(`/scans/${id}`, { method: "DELETE" }),
};

/**
 * Note: WebSocket connections cannot carry httpOnly cookies the same way fetch does
 * in every browser/proxy configuration. For same-origin local dev this works because
 * the browser attaches the cookie automatically on the WS upgrade request. In production
 * behind a reverse proxy/ingress on the same domain, this also works. If you deploy the
 * frontend and backend on different domains, replace this with a short-lived WS ticket
 * fetched from a same-origin Next.js route that reads the httpOnly cookie server-side.
 */
export function createWsUrl(scanId: string): string {
  const ws = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
  return `${ws}/api/v1/scans/ws/${scanId}`;
}
