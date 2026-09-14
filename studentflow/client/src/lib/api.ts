const API_ROOT = import.meta.env.VITE_API_URL ?? "/api/v1";
let csrfToken = "";
let csrfRequest: Promise<string> | null = null;

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

async function ensureCsrf(): Promise<string> {
  if (csrfToken) return csrfToken;
  if (!csrfRequest) {
    csrfRequest = fetch(`${API_ROOT}/auth/csrf`, { credentials: "include" })
      .then(async (response) => {
        if (!response.ok) throw new ApiError(response.status, "csrf_failed", "요청 검증에 실패했습니다.");
        const data = await response.json();
        csrfToken = data.csrf_token;
        return csrfToken;
      })
      .finally(() => { csrfRequest = null; });
  }
  return csrfRequest;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  const requiresCsrf = !["GET", "HEAD", "OPTIONS"].includes(method);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (requiresCsrf) headers.set("X-CSRF-Token", await ensureCsrf());

  let response = await fetch(`${API_ROOT}${path}`, { ...init, headers, credentials: "include" });
  if (response.status === 401 && !["/auth/login", "/auth/refresh"].includes(path)) {
    const refreshHeaders = new Headers({ "X-CSRF-Token": await ensureCsrf() });
    const refreshed = await fetch(`${API_ROOT}/auth/refresh`, { method: "POST", credentials: "include", headers: refreshHeaders });
    if (refreshed.ok) {
      csrfToken = "";
      if (requiresCsrf) headers.set("X-CSRF-Token", await ensureCsrf());
      response = await fetch(`${API_ROOT}${path}`, { ...init, headers, credentials: "include" });
    }
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ code: "unknown", detail: "요청을 처리하지 못했습니다." }));
    throw new ApiError(response.status, error.code ?? "unknown", error.detail ?? "요청을 처리하지 못했습니다.");
  }
  if (
    ["/auth/login", "/auth/refresh", "/auth/logout"].includes(path) ||
    path.startsWith("/auth/test-switch/")
  )
    csrfToken = "";
  if (response.status === 204) return undefined as T;
  return response.json();
}

export const jsonBody = (value: unknown): Pick<RequestInit, "body"> => ({ body: JSON.stringify(value) });
