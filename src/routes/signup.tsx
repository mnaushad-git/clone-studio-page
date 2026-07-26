import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import illustration from "@/assets/signup-illustration.jpg";
import { auth, addresses as addressStore } from "@/lib/store";

const AREAS = ["Riyadh", "Jeddah", "Dammam"] as const;

const signupSchema = z
  .object({
    name: z.string().trim().min(1, "Name is required").max(100),
    email: z.string().trim().email("Enter a valid email").max(255),
    phone: z.string().trim().min(6, "Phone is required").max(20),
    area: z.string().trim().min(1, "Area is required"),
    address: z.string().trim().min(3, "Address is required").max(200),
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

function Field({ label, error, ...props }: { label: string; error?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      <label className="block text-sm font-medium mb-2">
        {label} <span className="text-destructive">*</span>
      </label>
      <input
        {...props}
        aria-invalid={!!error}
        className={`w-full border rounded-md px-4 py-3 text-sm focus:outline-none bg-white ${error ? "border-destructive focus:border-destructive" : "border-border focus:border-primary"}`}
      />
      {error && <p className="text-xs text-destructive mt-1">{error}</p>}
    </div>
  );
}

function SignupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone: "", area: "", address: "", password: "", confirm: "" });
  const [errors, setErrors] = useState<Partial<Record<keyof typeof form, string>>>({});
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm({ ...form, [k]: e.target.value });
    if (errors[k]) setErrors({ ...errors, [k]: undefined });
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const result = signupSchema.safeParse(form);
    if (!result.success) {
      const fieldErrors: Partial<Record<keyof typeof form, string>> = {};
      for (const issue of result.error.issues) {
        const key = issue.path[0] as keyof typeof form;
        if (key && !fieldErrors[key]) fieldErrors[key] = issue.message;
      }
      setErrors(fieldErrors);
      toast.error("Please fix the errors and try again");
      return;
    }
    setErrors({});
    auth.signIn({ name: form.name, email: form.email, phone: form.phone });
    addressStore.add({
      name: form.name,
      phone: form.phone.startsWith("+966") ? form.phone : `+966 ${form.phone.replace(/^\+?/, "")}`,
      area: form.area,
      address: form.address,
      isGift: false,
    });
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

          <form className="space-y-4" onSubmit={submit} noValidate>
            <Field label="Name" placeholder="Enter your name" required value={form.name} error={errors.name} onChange={set("name")} />
            <Field label="Email" type="email" placeholder="you@example.com" required value={form.email} error={errors.email} onChange={set("email")} />
            <Field label="Phone" type="tel" placeholder="+888 2148956" required value={form.phone} error={errors.phone} onChange={set("phone")} />
            <Field label="New Password" type="password" placeholder="* * * * * * * *" required value={form.password} error={errors.password} onChange={set("password")} />
            <Field label="Confirm Password" type="password" placeholder="* * * * * * * *" required value={form.confirm} error={errors.confirm} onChange={set("confirm")} />

            <button type="submit" className="w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition">
              Sign Up
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            Already have an account? <Link to="/login" className="font-semibold text-foreground hover:text-primary">Sign In</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
