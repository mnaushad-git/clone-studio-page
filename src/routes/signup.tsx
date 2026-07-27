import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import illustration from "@/assets/signup-illustration.jpg";
import { auth, addresses as addressStore, RIYADH_AREAS } from "@/lib/store";
import { useT } from "@/lib/i18n";

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
  const t = useT();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", phone: "", area: "", address: "", password: "", confirm: "" });
  const [errors, setErrors] = useState<Partial<Record<keyof typeof form, string>>>({});
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm({ ...form, [k]: e.target.value });
    if (errors[k]) setErrors({ ...errors, [k]: undefined });
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const signupSchema = z
      .object({
        name: z.string().trim().min(1, t("accountSignupErrorNameRequired")).max(100),
        email: z.string().trim().email(t("accountSignupErrorEmailInvalid")).max(255),
        phone: z.string().trim().min(6, t("accountSignupErrorPhoneRequired")).max(20),
        area: z.string().trim().min(1, t("accountSignupErrorAreaRequired")),
        address: z.string().trim().min(3, t("accountSignupErrorAddressRequired")).max(200),
        password: z.string().min(8, t("accountSignupErrorPasswordMin")).max(100),
        confirm: z.string().min(1, t("accountSignupErrorConfirmRequired")),
      })
      .refine((d) => d.password === d.confirm, { path: ["confirm"], message: t("accountSignupToastPasswordsMismatch") });

    const result = signupSchema.safeParse(form);
    if (!result.success) {
      const fieldErrors: Partial<Record<keyof typeof form, string>> = {};
      for (const issue of result.error.issues) {
        const key = issue.path[0] as keyof typeof form;
        if (key && !fieldErrors[key]) fieldErrors[key] = issue.message;
      }
      setErrors(fieldErrors);
      toast.error(t("accountSignupToastFixErrors"));
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
    toast.success(t("accountSignupToastAccountCreated"));
    navigate({ to: "/account" });
  };

  return (
    <div className="min-h-screen bg-secondary flex items-stretch">
      <div className="hidden md:flex md:w-1/2 items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute top-6 left-6 w-40 h-40 rounded-full border-[10px] border-white/60" />
        <div className="absolute top-14 left-14 w-24 h-24 rounded-full border-[8px] border-white/60" />
        <div className="text-center max-w-md relative">
          <h2 className="font-display text-3xl md:text-4xl text-foreground leading-tight">
            {t("accountSignupHeroTitle")}
          </h2>
          <img src={illustration} alt={t("accountSignupIllustrationAlt")} className="mt-10 w-full max-w-md mx-auto" />
        </div>
      </div>

      <div className="w-full md:w-1/2 bg-background rounded-l-3xl p-8 md:p-14 flex items-center">
        <div className="w-full max-w-md mx-auto">
          <h1 className="font-display text-3xl md:text-4xl text-primary text-center mb-8">{t("accountSignupTitle")}</h1>

          <form className="space-y-4" onSubmit={submit} noValidate>
            <Field label={t("accountSignupFieldName")} placeholder={t("accountSignupPlaceholderName")} required value={form.name} error={errors.name} onChange={set("name")} />
            <Field label={t("accountSignupFieldEmail")} type="email" placeholder="you@example.com" required value={form.email} error={errors.email} onChange={set("email")} />
            <Field label={t("accountSignupFieldPhone")} type="tel" placeholder="+888 2148956" required value={form.phone} error={errors.phone} onChange={set("phone")} />

            <div>
              <label className="block text-sm font-medium mb-2">
                {t("accountSignupFieldArea")} <span className="text-destructive">*</span>
              </label>
              <select
                value={form.area}
                onChange={set("area")}
                aria-invalid={!!errors.area}
                className={`w-full border rounded-md px-4 py-3 text-sm focus:outline-none bg-white ${errors.area ? "border-destructive focus:border-destructive" : "border-border focus:border-primary"}`}
              >
                <option value="">{t("accountSelectAreaOption")}</option>
                {RIYADH_AREAS.map((area) => <option key={area} value={area}>{area}</option>)}
              </select>
              {errors.area && <p className="text-xs text-destructive mt-1">{errors.area}</p>}
            </div>
            <Field label={t("accountSignupFieldAddress")} placeholder={t("accountSignupPlaceholderAddress")} required value={form.address} error={errors.address} onChange={set("address")} />

            <Field label={t("accountSignupFieldNewPassword")} type="password" placeholder="* * * * * * * *" required value={form.password} error={errors.password} onChange={set("password")} />
            <Field label={t("accountSignupFieldConfirmPassword")} type="password" placeholder="* * * * * * * *" required value={form.confirm} error={errors.confirm} onChange={set("confirm")} />


            <button type="submit" className="w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition">
              {t("accountSignupSubmitButton")}
            </button>
          </form>

          <p className="text-center text-sm text-muted-foreground mt-6">
            {t("accountSignupHaveAccountPrefix")} <Link to="/login" className="font-semibold text-foreground hover:text-primary">{t("accountSignupSignInLink")}</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
