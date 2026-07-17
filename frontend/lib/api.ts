const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Optional auth token — set by the auth context before making requests. */
let authToken: string | null = null;

/** Attach a Bearer token to all subsequent requests. Called by auth context. */
export function setAuthToken(token: string | null): void {
  authToken = token;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...headers, ...(options?.headers ?? {}) },
    ...options,
  });

  if (!res.ok) {
    // Token expired or invalid — notify auth context to clear state
    if (res.status === 401) {
      setAuthToken(null);
    }

    let message = `API ${res.status}`;
    try {
      const body = await res.json();
      message = body.error || body.detail || message;
    } catch {
      message = `${message}: ${await res.text()}`;
    }
    throw new Error(message);
  }

  return res.json();
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },

  post<T, B = unknown>(path: string, body: B): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  put<T, B = unknown>(path: string, body: B): Promise<T> {
    return request<T>(path, {
      method: "PUT",
      body: JSON.stringify(body),
    });
  },

  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: "DELETE" });
  },
};

/** Unwrap the backend APIResponse envelope: { success, data, error }. */
export async function unwrap<T>(raw: unknown): Promise<T[]> {
  if (raw == null) return [];
  // Backend wraps list endpoints in { success, data: T[], error }
  if (typeof raw === "object" && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    if ("data" in obj && Array.isArray(obj.data)) return obj.data as T[];
  }
  // Fallback: treat the raw value as the array directly
  return Array.isArray(raw) ? (raw as T[]) : [];
}

/** Unwrap single-object responses: { success, data: T, error }. */
export async function unwrapSingle<T>(raw: unknown): Promise<T> {
  if (raw == null) return null as unknown as T;
  if (typeof raw === "object" && !Array.isArray(raw)) {
    const obj = raw as Record<string, unknown>;
    if ("data" in obj) return obj.data as T;
  }
  return raw as T;
}
