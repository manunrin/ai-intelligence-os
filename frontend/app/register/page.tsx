"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useAuth } from "@/lib/auth-context";
import { api, setAuthToken, unwrapSingle } from "@/lib/api";
import type { User } from "@/lib/auth-context";

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setError(null);

      if (password !== confirmPassword) {
        setError("Passwords do not match");
        return;
      }

      if (password.length < 8) {
        setError("Password must be at least 8 characters");
        return;
      }

      setLoading(true);

      try {
        // Register
        await api.post<unknown>("/api/v1/auth/register", { username, email, password });

        // Auto-login
        const loginRes = await api.post<unknown>("/api/v1/auth/login", { username, password });
        const { access_token } = await unwrapSingle<{ access_token: string; token_type: string }>(loginRes);
        setAuthToken(access_token);

        // Fetch user profile
        const meRes = await api.get<unknown>("/api/v1/auth/me");
        const userData = await unwrapSingle<User>(meRes);
        login(access_token, userData);
        router.push("/");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Registration failed");
      } finally {
        setLoading(false);
      }
    },
    [username, email, password, confirmPassword, login, router]
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
            Create your account
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
              placeholder="Choose a username (3+ chars)"
              required
              minLength={3}
              maxLength={64}
              autoComplete="username"
            />

            <Input
              label="Email"
              name="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              required
              autoComplete="email"
            />

            <Input
              label="Password"
              name="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
              required
              minLength={8}
              autoComplete="new-password"
            />

            <Input
              label="Confirm Password"
              name="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your password"
              required
              autoComplete="new-password"
            />

            <Button
              type="submit"
              className="w-full"
              disabled={loading || !username || !email || !password || !confirmPassword}
            >
              {loading ? "Creating account..." : "Create account"}
            </Button>
          </form>

          <p className="text-center text-sm text-slate-500 dark:text-slate-400">
            Already have an account?{" "}
            <a href="/login" className="text-blue-600 hover:underline dark:text-blue-400">
              Sign in
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
