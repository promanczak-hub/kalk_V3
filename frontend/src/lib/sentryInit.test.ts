/**
 * Tests for `initSentry` — verify the no-op path when VITE_SENTRY_DSN is
 * missing (dev / unconfigured environments), and that beforeSend scrubs
 * request bodies/cookies before events leave the process.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const sentryInitSpy = vi.fn();

vi.mock("@sentry/react", () => ({
  init: (config: unknown) => sentryInitSpy(config),
  browserTracingIntegration: () => "browser-tracing",
  browserApiErrorsIntegration: () => "browser-api-errors",
}));

describe("initSentry", () => {
  const originalEnv = { ...import.meta.env };

  beforeEach(() => {
    sentryInitSpy.mockReset();
  });

  afterEach(() => {
    Object.assign(import.meta.env, originalEnv);
    vi.resetModules();
  });

  it("returns false and skips Sentry.init when VITE_SENTRY_DSN is missing", async () => {
    (import.meta.env as Record<string, string | undefined>).VITE_SENTRY_DSN = "";
    const { initSentry } = await import("./sentryInit");
    expect(initSentry()).toBe(false);
    expect(sentryInitSpy).not.toHaveBeenCalled();
  });

  it("initialises with environment + release when DSN is set", async () => {
    (import.meta.env as Record<string, string | undefined>).VITE_SENTRY_DSN = "https://x@x.ingest.sentry.io/1";
    (import.meta.env as Record<string, string | undefined>).VITE_SENTRY_ENVIRONMENT = "production";
    (import.meta.env as Record<string, string | undefined>).VITE_SENTRY_RELEASE = "abc123";

    const { initSentry } = await import("./sentryInit");
    expect(initSentry()).toBe(true);
    expect(sentryInitSpy).toHaveBeenCalledOnce();
    const config = sentryInitSpy.mock.calls[0][0] as Record<string, unknown>;
    expect(config.dsn).toBe("https://x@x.ingest.sentry.io/1");
    expect(config.environment).toBe("production");
    expect(config.release).toBe("abc123");
    expect(config.sendDefaultPii).toBe(false);
  });

  it("beforeSend strips request.data and request.cookies", async () => {
    (import.meta.env as Record<string, string | undefined>).VITE_SENTRY_DSN = "https://x@x.ingest.sentry.io/2";

    const { initSentry } = await import("./sentryInit");
    initSentry();
    const config = sentryInitSpy.mock.calls[0][0] as {
      beforeSend: (event: unknown) => unknown;
    };

    const event = {
      message: "Test",
      request: {
        url: "/x",
        data: { vehicleId: "secret-vid", base_price: 123000 },
        cookies: { session: "very-secret" },
        headers: { "User-Agent": "test" },
      },
    };
    const cleaned = config.beforeSend(event) as typeof event;
    expect(cleaned.request.data).toBeUndefined();
    expect(cleaned.request.cookies).toBeUndefined();
    expect(cleaned.request.headers).toEqual({ "User-Agent": "test" });
  });
});
