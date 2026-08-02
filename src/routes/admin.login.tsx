import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { login, AdminApiError } from "@/lib/admin-api";
import { Lock } from "lucide-react";

export const Route = createFileRoute("/admin/login")({
  component: AdminLogin,
  head: () => ({
    meta: [{ title: "Admin sign in — Terrific Bites" }, { name: "robots", content: "noindex" }],
  }),
});

function AdminLogin() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const admin = await login(email, password);
      queryClient.setQueryData(["admin", "me"], admin);
      navigate({ to: "/admin" });
    } catch (err) {
      setError(err instanceof AdminApiError ? err.message : "Sign in failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-primary flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8">
        <div className="flex flex-col items-center mb-6">
          <div className="h-12 w-12 rounded-full bg-primary flex items-center justify-center mb-3">
            <Lock className="h-5 w-5 text-amber-300" />
          </div>
          <h1 className="font-display text-2xl text-stone-800">Admin Portal</h1>
          <p className="text-sm text-stone-500 mt-1">Terrific Bites — Staff sign in</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label htmlFor="admin-login-email" className="text-xs font-medium text-stone-600">
              Work email
            </label>
            <input
              id="admin-login-email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              required
              className="mt-1 w-full h-11 px-3 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none"
            />
          </div>
          <div>
            <label htmlFor="admin-login-password" className="text-xs font-medium text-stone-600">
              Password
            </label>
            <input
              id="admin-login-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              required
              className="mt-1 w-full h-11 px-3 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none"
            />
          </div>
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={submitting}
            className="w-full h-11 rounded-lg bg-stone-900 text-white font-medium hover:bg-stone-800 disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
