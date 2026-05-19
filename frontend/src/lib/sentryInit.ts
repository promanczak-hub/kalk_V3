/**
 * Sentry initialisation for the kalk_v3 frontend.
 *
 * Imported by `src/main.tsx` BEFORE the React app mounts. No-op when
 * `VITE_SENTRY_DSN` is missing, so dev runs are unaffected.
 *
 * Pairs with the backend's request-ID propagation in `core/sentry_init.py` —
 * the FE attaches the same request_id to outbound requests when emitted
 * by `apiClient.fetch`, so errors caught here can be correlated 1:1 with
 * the backend trace.
 */

import * as Sentry from "@sentry/react";

interface SentryEnv {
  VITE_SENTRY_DSN?: string;
  VITE_SENTRY_ENVIRONMENT?: string;
  VITE_SENTRY_RELEASE?: string;
  VITE_SENTRY_TRACES_SAMPLE_RATE?: string;
}

export function initSentry(): boolean {
  const env = import.meta.env as unknown as SentryEnv;
  const dsn = env.VITE_SENTRY_DSN;
  if (!dsn) {
    return false;
  }

  Sentry.init({
    dsn,
    environment: env.VITE_SENTRY_ENVIRONMENT ?? "development",
    release: env.VITE_SENTRY_RELEASE,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.browserApiErrorsIntegration(),
    ],
    tracesSampleRate: Number(env.VITE_SENTRY_TRACES_SAMPLE_RATE ?? "0.05"),
    // Don't auto-attach IP, headers, query strings.
    sendDefaultPii: false,
    // Drop request bodies; calculation payloads contain vehicle data we
    // don't want shipped to Sentry verbatim. Backend has matching scrubbing.
    beforeSend(event) {
      if (event.request) {
        delete event.request.data;
        delete event.request.cookies;
      }
      return event;
    },
  });

  return true;
}

export { Sentry };
