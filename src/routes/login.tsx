import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { User, X } from "lucide-react";

export const Route = createFileRoute("/login")({
  component: LoginPage,
  head: () => ({
    meta: [
      { title: "Login — Terrific Bites" },
      { name: "description", content: "Sign in to your Terrific Bites account with your mobile number to order desserts and track rewards." },
      { property: "og:title", content: "Login — Terrific Bites" },
      { property: "og:description", content: "Sign in to Terrific Bites to order desserts and earn rewards." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

function LoginPage() {
  const [mode, setMode] = useState<"phone" | "email">("phone");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div className="min-h-screen bg-black/40 flex items-center justify-center p-4">
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-10">
        <Link to="/" className="absolute top-5 right-5 text-foreground hover:text-primary" aria-label="Close">
          <X className="h-5 w-5" />
        </Link>

        <div className="flex flex-col items-center">
          <div className="h-14 w-14 rounded-full bg-secondary flex items-center justify-center shadow-sm">
            <User className="h-6 w-6 text-primary" />
          </div>
          <h1 className="font-display text-2xl text-primary mt-4">Login</h1>
        </div>

        <form className="mt-8 space-y-5" onSubmit={(e) => e.preventDefault()}>
          {mode === "phone" ? (
            <div>
              <label className="block text-sm font-semibold mb-2">Mobile Number</label>
              <div className="flex items-center border border-border rounded-md overflow-hidden focus-within:border-primary">
                <span className="px-4 py-3 text-sm border-r border-border text-foreground">+966</span>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="214 895 62147"
                  className="flex-1 px-4 py-3 text-sm outline-none bg-transparent"
                />
              </div>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-semibold mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="* * * * * * * *"
                  className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-transparent"
                />
                <div className="text-right mt-2">
                  <a href="#" className="text-xs text-muted-foreground hover:text-primary">Forgot password?</a>
                </div>
              </div>
            </>
          )}

          <button type="submit" className="w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition">
            Enter
          </button>
        </form>

        <div className="text-center mt-5">
          <button
            type="button"
            onClick={() => setMode(mode === "phone" ? "email" : "phone")}
            className="text-sm text-foreground hover:text-primary underline-offset-2 hover:underline"
          >
            {mode === "phone" ? "Sign in with email" : "Sign in with mobile number"}
          </button>
        </div>

        <p className="text-center text-xs text-muted-foreground mt-4">
          Don't have an account? <Link to="/signup" className="font-semibold text-foreground hover:text-primary">Sign up</Link>
        </p>
      </div>
    </div>
  );
}
