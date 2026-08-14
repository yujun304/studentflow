import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe("api CSRF synchronization", () => {
  it("shares one CSRF request between concurrent mutations", async () => {
    let csrfCalls = 0;
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/auth/csrf")) {
        csrfCalls += 1;
        return Response.json({ csrf_token: "shared-token" });
      }
      expect(new Headers(init?.headers).get("X-CSRF-Token")).toBe("shared-token");
      return Response.json({ ok: true });
    });
    vi.stubGlobal("fetch", fetchMock);
    const { api } = await import("./api");

    await Promise.all([
      api("/tasks/one", { method: "PATCH", body: "{}" }),
      api("/tasks/two", { method: "PATCH", body: "{}" }),
    ]);

    expect(csrfCalls).toBe(1);
  });

  it("reloads the CSRF token after login rotates the cookie", async () => {
    let csrfCalls = 0;
    const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const url = input.toString();
      if (url.endsWith("/auth/csrf")) {
        csrfCalls += 1;
        return Response.json({ csrf_token: csrfCalls === 1 ? "before-login" : "after-login" });
      }
      const token = new Headers(init?.headers).get("X-CSRF-Token");
      if (url.endsWith("/auth/login")) {
        expect(token).toBe("before-login");
        return Response.json({ email: "teacher@example.com", role: "TEACHER" });
      }
      expect(token).toBe("after-login");
      return Response.json({ ok: true });
    });
    vi.stubGlobal("fetch", fetchMock);
    const { api } = await import("./api");

    await api("/auth/login", { method: "POST", body: "{}" });
    await api("/tasks/one", { method: "PATCH", body: "{}" });

    expect(csrfCalls).toBe(2);
  });
});
