"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useAuth } from "@/lib/auth-context";
import { api, setAuthToken, unwrapSingle } from "@/lib/api";
import type { User } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const callbackUrl = searchParams.get("callbackUrl") || "/";

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);
      setLoading(true);

      try {
        // Login
        const loginRes = await api.post<unknown>("/api/v1/auth/login", { username, password });
        const { access_token } = await unwrapSingle<{ access_token: string; token_type: string }>(loginRes);
        setAuthToken(access_token);

        // Fetch user profile
        const meRes = await api.get<unknown>("/api/v1/auth/me");
        const userData = await unwrapSingle<User>(meRes);
        login(access_token, userData);
        router.push(callbackUrl);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Login failed");
      } finally {
        setLoading(false);
      }
    },
    [username, password, login, router, callbackUrl]
  );

  return (
    <main className="min-h-screen bg-[var(--background)] flex items-center justify-center p-6 dark:bg-[var(--background)]">
      <div className="w-full max-w-md space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            AI Intelligence OS
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Sign in to your account
          </p>
        </div>

        {/* Form Card */}
        <div className="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900 p-6 space-y-4">
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              name="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
              autoComplete="username"
            />

            <Input
              label="Password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              autoComplete="current-password"
            />

            <Button
              type="submit"
              className="w-full"
              disabled={loading || !username || !password}
            >
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <p className="text-center text-sm text-slate-500 dark:text-slate-400">
            Don&apos;t have an account?{" "}
            <a href="/register" className="text-blue-600 hover:underline dark:text-blue-400">
              Create one
            </a>
          </p>
        </div>

        {/* Connection status */}
        <div className="flex items-center justify-center gap-2 text-xs text-slate-400">
          <Badge variant="success">Connected</Badge>
          <span>Backend available</span>
        </div>
      </div>
    </main>
  );
}
