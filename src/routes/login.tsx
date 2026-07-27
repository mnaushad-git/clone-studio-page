import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { User, X, ArrowLeft } from "lucide-react";
import { toast } from "sonner";
import { auth } from "@/lib/store";
import { useT } from "@/lib/i18n";

export const Route = createFileRoute("/login")({
  component: LoginPage,
  validateSearch: (search: Record<string, unknown>): { redirect?: string } => ({
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Login — Terrific Bites" },
      { name: "description", content: "Sign in to your Terrific Bites account." },
      { property: "og:title", content: "Login — Terrific Bites" },
      { property: "og:description", content: "Sign in to order desserts and track rewards." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

function LoginPage() {
  const t = useT();
  const navigate = useNavigate();
  const { redirect } = Route.useSearch();
  const [mode, setMode] = useState<"phone" | "email" | "otp">("phone");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otp, setOtp] = useState<string[]>(["", "", "", ""]);
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  const finish = (user: { phone?: string; email?: string }) => {
    auth.signIn(user);
    toast.success(t("accountLoginToastWelcomeBack"));
    const dest = redirect && redirect.startsWith("/") ? redirect : "/account";
    navigate({ to: dest });
  };

  const handleOtpChange = (i: number, v: string) => {
    const ch = v.replace(/\D/g, "").slice(-1);
    const next = [...otp];
    next[i] = ch;
    setOtp(next);
    if (ch && i < 3) otpRefs.current[i + 1]?.focus();
    if (i === 3 && ch && next.every(Boolean)) {
      setTimeout(() => finish({ phone: `+966 ${phone}` }), 300);
    }
  };

  const handleOtpKey = (i: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) otpRefs.current[i - 1]?.focus();
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (mode === "phone") {
      if (!phone.trim()) return toast.error(t("accountLoginToastEnterMobile"));
      setOtp(["", "", "", ""]);
      setMode("otp");
      setTimeout(() => otpRefs.current[0]?.focus(), 0);
      toast.info(t("accountLoginToastOtpSentDemo"));
    } else if (mode === "email") {
      if (!email.trim() || !password) return toast.error(t("accountLoginToastEnterEmailPassword"));
      finish({ email });
    }
  };

  const verifyOtp = (e: React.FormEvent) => {
    e.preventDefault();
    if (otp.some((d) => !d)) return;
    finish({ phone: `+966 ${phone}` });
  };

  return (
    <div className="min-h-screen bg-black/40 flex items-center justify-center p-4">
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-10">
        <Link to="/" className="absolute top-5 right-5 text-foreground hover:text-primary" aria-label={t("accountLoginCloseAriaLabel")}>
          <X className="h-5 w-5" />
        </Link>
        {mode === "otp" && (
          <button type="button" onClick={() => setMode("phone")} className="absolute top-5 left-5 text-foreground hover:text-primary" aria-label={t("accountLoginBackAriaLabel")}>
            <ArrowLeft className="h-5 w-5" />
          </button>
        )}

        <div className="flex flex-col items-center">
          <div className="h-14 w-14 rounded-full bg-secondary flex items-center justify-center shadow-sm">
            <User className="h-6 w-6 text-primary" />
          </div>
          <h1 className="font-display text-2xl text-primary mt-4">
            {mode === "otp" ? t("accountLoginVerifyTitle") : t("accountLoginTitle")}
          </h1>
          {mode === "otp" && (
            <p className="text-xs text-muted-foreground mt-2 text-center">
              {t("accountLoginOtpSentTo")}<br />
              <span className="font-semibold text-foreground">+966 {phone}</span>
            </p>
          )}
        </div>

        {mode === "otp" ? (
          <form className="mt-8 space-y-5" onSubmit={verifyOtp}>
            <div className="flex justify-center gap-3">
              {otp.map((d, i) => (
                <input
                  key={i}
                  ref={(el) => { otpRefs.current[i] = el; }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={d}
                  onChange={(e) => handleOtpChange(i, e.target.value)}
                  onKeyDown={(e) => handleOtpKey(i, e)}
                  className="w-14 h-14 text-center text-xl font-semibold border border-border rounded-md outline-none focus:border-primary bg-transparent"
                />
              ))}
            </div>
            <button type="submit" disabled={otp.some((d) => !d)} className="w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed">
              {t("accountLoginVerifyButton")}
            </button>
            <div className="text-center">
              <button type="button" onClick={() => toast.info(t("accountLoginToastCodeResent"))} className="text-sm text-foreground hover:text-primary underline-offset-2 hover:underline">
                {t("accountLoginResendCode")}
              </button>
            </div>
          </form>
        ) : (
          <>
            <form className="mt-8 space-y-5" onSubmit={submit}>
              {mode === "phone" ? (
                <div>
                  <label className="block text-sm font-semibold mb-2">{t("accountLoginMobileLabel")}</label>
                  <div className="flex items-center border border-border rounded-md overflow-hidden focus-within:border-primary">
                    <span className="px-4 py-3 text-sm border-r border-border text-foreground">+966</span>
                    <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 15))} placeholder="214 895 62147" className="flex-1 px-4 py-3 text-sm outline-none bg-transparent" />
                  </div>
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-sm font-semibold mb-2">{t("accountLoginEmailLabel")}</label>
                    <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-transparent" />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold mb-2">{t("accountLoginPasswordLabel")}</label>
                    <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="* * * * * * * *" className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-transparent" />
                    <div className="text-right mt-2">
                      <Link to="/forgot-password" className="text-xs text-muted-foreground hover:text-primary">{t("accountLoginForgotPassword")}</Link>
                    </div>

                  </div>
                </>
              )}
              <button type="submit" className="w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition">{t("accountLoginEnterButton")}</button>
            </form>

            <div className="text-center mt-5">
              <button type="button" onClick={() => setMode(mode === "phone" ? "email" : "phone")} className="text-sm text-foreground hover:text-primary underline-offset-2 hover:underline">
                {mode === "phone" ? t("accountLoginSwitchToEmail") : t("accountLoginSwitchToMobile")}
              </button>
            </div>

            <p className="text-center text-xs text-muted-foreground mt-4">
              {t("accountLoginNoAccountPrefix")} <Link to="/signup" className="font-semibold text-foreground hover:text-primary">{t("accountLoginSignUpLink")}</Link>
            </p>
          </>
        )}
      </div>
    </div>
  );
}
