/**
 * Framework-agnostic token manager.
 *
 * Single source of truth for the access token and the refresh gate.
 * Used by api.ts (interceptor) and auth-context.tsx (state sync).
 *
 * Invariants:
 *  - Only one /auth/refresh request in flight at a time.
 *    Concurrent callers share the same Promise.
 *  - No React imports — plain JS module.
 */

// ── Access token state ────────────────────────────────────────────────

let _accessToken: string | null = null;

export function getAccessToken(): string | null {
  return _accessToken;
}

export function setAccessToken(token: string): void {
  _accessToken = token;
  document.cookie = `aio_auth_token=${token}; path=/; SameSite=Lax`;
}

export function clearAccessToken(): void {
  _accessToken = null;
  document.cookie = "aio_auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
}

// ── Refresh gate ──────────────────────────────────────────────────────

let _refreshPromise: Promise<string> | null = null;

const AUTH_ENDPOINTS = [
  "/api/v1/auth/login",
  "/api/v1/auth/register",
  "/api/v1/auth/refresh",
  "/api/v1/auth/logout",
];

export function isAuthEndpoint(path: string): boolean {
  return AUTH_ENDPOINTS.some((ep) => path === ep || path.startsWith(ep + "/"));
}

/**
 * Exchange the HttpOnly refresh cookie for a new access token.
 *
 * - Exactly one fetch is ever in flight; concurrent calls share the Promise.
 * - On success: resolves with the new token string.
 * - On 401/403 (invalid/expired refresh token): rejects — caller should clear auth.
 * - On network error or 5xx: rejects — caller should NOT clear auth (transient).
 */
export async function refreshAccessToken(): Promise<string> {
  // If a refresh is already in flight, share its Promise.
  if (_refreshPromise !== null) {
    return _refreshPromise;
  }

  const promise = (async () => {
    try {
      const res = await fetch("/api/v1/auth/refresh", { method: "POST" });

      if (!res.ok) {
        // 401/403 → refresh token invalid/expired → fatal auth failure
        if (res.status === 401 || res.status === 403) {
          throw new Error("Refresh token invalid or expired");
        }
        // 5xx or other non-auth errors → transient, do NOT clear auth
        throw new Error(`Refresh failed with status ${res.status}`);
      }

      const json = await res.json();
      const token = json?.data?.access_token;
      if (!token) {
        throw new Error("Missing access_token in refresh response");
      }
      return token;
    } finally {
      // Always clear the gate so future requests can retry.
      _refreshPromise = null;
    }
  })();

  _refreshPromise = promise;
  return promise;
}
