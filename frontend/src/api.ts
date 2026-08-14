const API = import.meta.env.VITE_API_URL ?? "/api/v1";
let csrfToken = "";
let csrfRequest: Promise<string> | null = null;

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  if (!csrfRequest) {
    csrfRequest = fetch(`${API}/auth/csrf`, { credentials: "include" })
      .then(async response => {
        if (!response.ok) throw new ApiError(response.status, "csrf_failed", "요청 검증에 실패했습니다.");
        const data = await response.json();
        csrfToken = data.csrf_token;
        return csrfToken;
      })
      .finally(() => { csrfRequest = null; });
  }
  return csrfRequest;
}

function resetCsrf() { csrfToken = ""; }

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const requiresCsrf = !["GET", "HEAD", "OPTIONS"].includes(method);
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (requiresCsrf) headers.set("X-CSRF-Token", await ensureCsrf());
  let response = await fetch(`${API}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 401 && path !== "/auth/refresh" && path !== "/auth/login") {
    const refreshed = await fetch(`${API}/auth/refresh`, { method: "POST", credentials: "include", headers: { "X-CSRF-Token": await ensureCsrf() } });
    if (refreshed.ok) {
      resetCsrf();
      if (requiresCsrf) headers.set("X-CSRF-Token", await ensureCsrf());
      response = await fetch(`${API}${path}`, { ...init, headers, credentials: "include" });
    }
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ code: "unknown", detail: "요청을 처리하지 못했습니다." }));
    throw new ApiError(response.status, error.code, error.detail);
  }
  if (["/auth/login", "/auth/refresh", "/auth/logout"].includes(path)) resetCsrf();
  if (response.status === 204) return undefined as T;
  return response.json();
}

export function jsonBody(value: unknown): Pick<RequestInit, "body"> { return { body: JSON.stringify(value) }; }
