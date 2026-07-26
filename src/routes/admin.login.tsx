import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { adminAuth } from "@/lib/admin-store";
import { Lock } from "lucide-react";

export const Route = createFileRoute("/admin/login")({
  component: AdminLogin,
  head: () => ({ meta: [{ title: "Admin sign in — Terrific Bites" }, { name: "robots", content: "noindex" }] }),
});

function AdminLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("owner@terrificbites.sa");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState<string | null>(null);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const res = adminAuth.signIn(email, password);
    if (!res.ok) return setError(res.error ?? "Sign in failed");
    navigate({ to: "/admin" });
  }

  return (
    <div className="min-h-screen bg-stone-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-2xl p-8">
        <div className="flex flex-col items-center mb-6">
          <div className="h-12 w-12 rounded-full bg-stone-900 flex items-center justify-center mb-3">
            <Lock className="h-5 w-5 text-amber-400" />
          </div>
          <h1 className="font-display text-2xl text-stone-800">Admin Portal</h1>
          <p className="text-sm text-stone-500 mt-1">Terrific Bites — Staff sign in</p>
        </div>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-stone-600">Work email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required className="mt-1 w-full h-11 px-3 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none" />
          </div>
          <div>
            <label className="text-xs font-medium text-stone-600">Password</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" required className="mt-1 w-full h-11 px-3 rounded-lg border border-stone-300 focus:border-stone-900 focus:outline-none" />
          </div>
          {error && <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}
          <button type="submit" className="w-full h-11 rounded-lg bg-stone-900 text-white font-medium hover:bg-stone-800">Sign in</button>
          <div className="text-xs text-stone-500 bg-stone-50 border border-stone-200 rounded-lg px-3 py-2">
            <strong>Demo:</strong> use any staff email from the seed (e.g. <code>owner@terrificbites.sa</code>) and password <code>admin123</code>.
          </div>
        </form>
      </div>
    </div>
  );
}
