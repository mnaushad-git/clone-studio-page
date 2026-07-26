import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import illustration from "@/assets/signup-illustration.jpg";
import { auth } from "@/lib/store";

const signupSchema = z
  .object({
    name: z.string().trim().min(1, "Name is required").max(100),
    email: z.string().trim().email("Enter a valid email").max(255),
    phone: z.string().trim().min(6, "Phone is required").max(20),
    password: z.string().min(8, "Password must be at least 8 characters").max(100),
    confirm: z.string().min(1, "Please confirm your password"),
  })
  .refine((d) => d.password === d.confirm, { path: ["confirm"], message: "Passwords don't match" });

export const Route = createFileRoute("/signup")({
  component: SignupPage,
  head: () => ({
    meta: [
      { title: "Create An Account — Terrific Bites" },
      { name: "description", content: "Sign up for a Terrific Bites account to order desserts and earn rewards." },
      { property: "og:title", content: "Create An Account — Terrific Bites" },
      { property: "og:description", content: "Join Terrific Bites for fresh desserts and member rewards." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

function Field({ label, ...props }: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <label className="block text-sm font-medium mb-2">{label}</label>
      <input {...props} className="w-full border border-border rounded-md px-4 py-3 text-sm focus:outline-none focus:border-primary bg-white" />
    </div>
  );
}

function SignupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone: "", password: "", confirm: "" });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || !form.password) return toast.error("Please fill in the required fields");
    if (form.password !== form.confirm) return toast.error("Passwords don't match");
    auth.signIn({ name: form.name, email: form.email, phone: form.phone });
    toast.success("Account created! Welcome to Terrific Bites.");
    navigate({ to: "/account" });
  };

  return (
    <div className="min-h-screen bg-secondary flex items-stretch">
      <div className="hidden md:flex md:w-1/2 items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute top-6 left-6 w-40 h-40 rounded-full border-[10px] border-white/60" />
        <div className="absolute top-14 left-14 w-24 h-24 rounded-full border-[8px] border-white/60" />
        <div className="text-center max-w-md relative">
          <h2 className="font-display text-3xl md:text-4xl text-foreground leading-tight">
            Welcome To Our Terrific<br />Bites Restaurant
          </h2>
          <img src={illustration} alt="Terrific Bites app illustration" className="mt-10 w-full max-w-md mx-auto" />
        </div>
      </div>

      <div className="w-full md:w-1/2 bg-background rounded-l-3xl p-8 md:p-14 flex items-center">
        <div className="w-full max-w-md mx-auto">
          <h1 className="font-display text-3xl md:text-4xl text-primary text-center mb-8">Create An Account</h1>

          <form className="space-y-4" onSubmit={submit}>
            <Field label="Name" placeholder="Enter your name" value={form.name} onChange={set("name")} />
            <Field label="Email" type="email" placeholder="you@example.com" value={form.email} onChange={set("email")} />
            <Field label="Phone" type="tel" placeholder="+888 2148956" value={form.phone} onChange={set("phone")} />
            <Field label="New Password" type="password" placeholder="* * * * * * * *" value={form.password} onChange={set("password")} />
            <Field label="Confirm Password" type="password" placeholder="* * * * * * * *" value={form.confirm} onChange={set("confirm")} />

            <button type="submit" className="w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition">
              Sign Up
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
            <div className="h-px flex-1 bg-border" /><span>Or</span><div className="h-px flex-1 bg-border" />
          </div>

          <div className="space-y-3">
            <button
              onClick={() => { auth.signIn({ name: "Facebook User", email: "fb@demo.com" }); toast.success("Signed in with Facebook"); navigate({ to: "/account" }); }}
              className="w-full bg-secondary rounded-md py-3 text-sm font-medium flex items-center justify-center gap-3 hover:bg-secondary/70 transition"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#1877F2"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/></svg>
              Continue with Facebook
            </button>
            <button
              onClick={() => { auth.signIn({ name: "Google User", email: "google@demo.com" }); toast.success("Signed in with Google"); navigate({ to: "/account" }); }}
              className="w-full bg-secondary rounded-md py-3 text-sm font-medium flex items-center justify-center gap-3 hover:bg-secondary/70 transition"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              Continue with Google
            </button>
          </div>

          <p className="text-center text-sm text-muted-foreground mt-6">
            Already have an account? <Link to="/login" className="font-semibold text-foreground hover:text-primary">Sign In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
