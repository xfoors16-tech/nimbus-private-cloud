import { describe, expect, it } from "vitest";
import { api, apiUrl, escapeHtml, formatBytes, getCsrfToken } from "./api.js";

describe("formatBytes", () => {
  it("formats empty and non-empty storage values", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(2 * 1024 ** 3)).toBe("2.0 GB");
  });
});

describe("browser-safe helpers", () => {
  it("keeps local API routes relative when no deployment URL is configured", () => {
    expect(apiUrl("/api/v1/health")).toBe("/api/v1/health");
  });

  it("reads and decodes the CSRF cookie", () => {
    expect(getCsrfToken("session=hidden; csrf_token=token%2Bvalue")).toBe("token+value");
    expect(getCsrfToken("session=hidden")).toBe("");
  });

  it("escapes user-controlled HTML", () => {
    expect(escapeHtml(`<img src="x" onerror='x'>`)).toBe("&lt;img src=&quot;x&quot; onerror=&#39;x&#39;&gt;");
  });

  it("keeps HTTP status on API errors for auth-state handling", async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: "Authentication required" }), { status: 401 });
    try {
      await expect(api("/api/v1/auth/me")).rejects.toMatchObject({ status: 401 });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
