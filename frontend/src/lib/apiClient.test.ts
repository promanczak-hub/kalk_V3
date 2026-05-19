/**
 * Tests for `apiClient.fetch` — covering the boundaries we care about:
 *  - Content-Type defaults applied to JSON, skipped for FormData
 *  - X-Request-ID always attached for FE↔BE log correlation (Sentry tag)
 *  - timeoutMs aborts in-flight requests and surfaces a Polish message
 *  - HTTP 4xx/5xx → ApiError with parsed detail/message
 *  - skipGlobalError prevents the Zustand global-error toast
 *  - Manual signal abort doesn't flip into a timeout error
 *
 * Mocks Zustand store, the env module, and global fetch.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient, ApiError } from "./apiClient";

const setGlobalErrorSpy = vi.fn();

vi.mock("../stores/useAppStore", () => ({
  useAppStore: {
    getState: () => ({ setGlobalError: setGlobalErrorSpy }),
  },
}));

vi.mock("../config/env", () => ({
  API_BASE_URL: "http://test.local",
}));

describe("apiClient.fetch", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    setGlobalErrorSpy.mockReset();
    fetchSpy = vi.spyOn(globalThis, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  function mockResponse(
    body: unknown,
    init: { status?: number; statusText?: string } = {},
  ): Response {
    return new Response(JSON.stringify(body), {
      status: init.status ?? 200,
      statusText: init.statusText ?? "OK",
      headers: { "Content-Type": "application/json" },
    });
  }

  it("prefixes API_BASE_URL when endpoint is relative", async () => {
    fetchSpy.mockResolvedValueOnce(mockResponse({ ok: true }));
    await apiClient.fetch("/api/ping");
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toBe("http://test.local/api/ping");
  });

  it("does not double-prefix absolute URLs", async () => {
    fetchSpy.mockResolvedValueOnce(mockResponse({ ok: true }));
    await apiClient.fetch("https://other.example.com/x");
    const calledUrl = fetchSpy.mock.calls[0][0] as string;
    expect(calledUrl).toBe("https://other.example.com/x");
  });

  it("sets Content-Type: application/json for non-FormData bodies", async () => {
    fetchSpy.mockResolvedValueOnce(mockResponse({ ok: true }));
    await apiClient.fetch("/p", { method: "POST", body: '{"a":1}' });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("does NOT set Content-Type when body is FormData", async () => {
    fetchSpy.mockResolvedValueOnce(mockResponse({ ok: true }));
    const fd = new FormData();
    fd.append("x", "1");
    await apiClient.fetch("/upload", { method: "POST", body: fd });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get("Content-Type")).toBeNull();
  });

  it("attaches an X-Request-ID header for FE↔BE correlation", async () => {
    fetchSpy.mockResolvedValueOnce(mockResponse({ ok: true }));
    await apiClient.fetch("/p");
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    const reqId = headers.get("X-Request-ID");
    expect(reqId).toBeTruthy();
    expect(reqId).toMatch(/^[0-9a-f-]{36}$/i);
  });

  it("honours a caller-supplied X-Request-ID", async () => {
    fetchSpy.mockResolvedValueOnce(mockResponse({ ok: true }));
    await apiClient.fetch("/p", { headers: { "X-Request-ID": "abc-123" } });
    const init = fetchSpy.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Headers;
    expect(headers.get("X-Request-ID")).toBe("abc-123");
  });

  it("throws ApiError with status + parsed detail on 4xx", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Not in catalog" }), {
        status: 404,
        statusText: "Not Found",
      }),
    );
    await expect(apiClient.fetch("/p", { skipGlobalError: true })).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "Not in catalog",
    });
  });

  it("falls back to response.statusText when body is not JSON", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response("plain text body", { status: 500, statusText: "Server boom" }),
    );
    await expect(apiClient.fetch("/p", { skipGlobalError: true })).rejects.toMatchObject({
      status: 500,
      message: "Server boom",
    });
  });

  it("joins FastAPI validation error arrays into one message", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          detail: [
            { msg: "field required: brand" },
            { msg: "field required: model" },
          ],
        }),
        { status: 422 },
      ),
    );
    await expect(apiClient.fetch("/p", { skipGlobalError: true })).rejects.toMatchObject({
      status: 422,
      message: "field required: brand, field required: model",
    });
  });

  it("propagates errors via Zustand setGlobalError by default", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Boom" }), { status: 500 }),
    );
    await expect(apiClient.fetch("/p")).rejects.toBeInstanceOf(ApiError);
    expect(setGlobalErrorSpy).toHaveBeenCalledWith("Boom");
  });

  it("does NOT call setGlobalError when skipGlobalError=true", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: "Boom" }), { status: 500 }),
    );
    await expect(
      apiClient.fetch("/p", { skipGlobalError: true }),
    ).rejects.toBeInstanceOf(ApiError);
    expect(setGlobalErrorSpy).not.toHaveBeenCalled();
  });

  it("surfaces the timeout message when the request hangs past timeoutMs", async () => {
    fetchSpy.mockImplementationOnce(
      (_url, init) =>
        new Promise((_, reject) => {
          const signal = (init as RequestInit).signal as AbortSignal;
          signal.addEventListener("abort", () => {
            const err = new Error("Aborted");
            err.name = "AbortError";
            reject(err);
          });
        }),
    );
    const promise = apiClient
      .fetch("/p", { timeoutMs: 5 })
      .catch((e) => e);
    const err = await promise;
    expect(err).toBeInstanceOf(Error);
    // The user-facing string is what the global error banner picks up.
    expect(setGlobalErrorSpy).toHaveBeenCalledWith(
      "Przekroczono czas oczekiwania na odpowiedź serwera (Timeout).",
    );
  });

  it("treats a caller's own AbortSignal as a manual abort (no global error)", async () => {
    const ctrl = new AbortController();
    fetchSpy.mockImplementationOnce(
      (_url, init) =>
        new Promise((_, reject) => {
          const signal = (init as RequestInit).signal as AbortSignal;
          signal.addEventListener("abort", () => {
            const err = new Error("Aborted");
            err.name = "AbortError";
            reject(err);
          });
        }),
    );
    const promise = apiClient
      .fetch("/p", { signal: ctrl.signal })
      .catch((e) => e);
    ctrl.abort();
    await promise;
    expect(setGlobalErrorSpy).not.toHaveBeenCalled();
  });
});
