import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Mail, X, ArrowLeft, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";

export const Route = createFileRoute("/forgot-password")({
  component: ForgotPasswordPage,
  head: () => ({
    meta: [
      { title: "Reset Password — Terrific Bites" },
      { name: "description", content: "Reset your Terrific Bites password via email." },
      { property: "og:title", content: "Reset Password — Terrific Bites" },
      { property: "og:description", content: "Recover access to your Terrific Bites account." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

const emailSchema = z.string().trim().email("Enter a valid email address");

function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = emailSchema.safeParse(email);
    if (!parsed.success) {
      setError(parsed.error.issues[0].message);
      return;
    }
    setError(null);
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setSent(true);
      toast.success("Reset link sent");
    }, 700);
  };

  const resend = () => {
    toast.info(`Reset link re-sent to ${email}`);
  };

  return (
    <div className="min-h-screen bg-black/40 flex items-center justify-center p-4">
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-10">
        <Link to="/" className="absolute top-5 right-5 text-foreground hover:text-primary" aria-label="Close">
          <X className="h-5 w-5" />
        </Link>
        {!sent && (
          <Link to="/login" className="absolute top-5 left-5 text-foreground hover:text-primary" aria-label="Back to login">
            <ArrowLeft className="h-5 w-5" />
          </Link>
        )}

        {!sent ? (
          <>
            <div className="flex flex-col items-center">
              <div className="h-14 w-14 rounded-full bg-secondary flex items-center justify-center shadow-sm">
                <Mail className="h-6 w-6 text-primary" />
              </div>
              <h1 className="font-display text-2xl text-primary mt-4">Forgot Password?</h1>
              <p className="text-xs text-muted-foreground mt-2 text-center px-4">
                Enter the email linked to your account and we'll send you a link to reset your password.
              </p>
            </div>

            <form className="mt-8 space-y-5" onSubmit={submit} noValidate>
              <div>
                <label className="block text-sm font-semibold mb-2">
                  Email <span className="text-red-500">*</span>
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => { setEmail(e.target.value); if (error) setError(null); }}
                  placeholder="you@example.com"
                  className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-transparent"
                  autoFocus
                />
                {error && <p className="mt-1 text-xs text-red-500">{error}</p>}
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition disabled:opacity-50"
              >
                {loading ? "Sending…" : "Send Reset Link"}
              </button>
            </form>

            <p className="text-center text-xs text-muted-foreground mt-6">
              Remembered it? <Link to="/login" className="font-semibold text-foreground hover:text-primary">Back to Login</Link>
            </p>
          </>
        ) : (
          <>
            <div className="flex flex-col items-center text-center">
              <div className="h-16 w-16 rounded-full bg-secondary flex items-center justify-center shadow-sm">
                <CheckCircle2 className="h-8 w-8 text-primary" />
              </div>
              <h1 className="font-display text-2xl text-primary mt-4">Check Your Email</h1>
              <p className="text-sm text-muted-foreground mt-3 px-2">
                We've sent a password reset link to
              </p>
              <p className="font-semibold text-foreground mt-1 break-all">{email}</p>
              <p className="text-xs text-muted-foreground mt-4 px-2">
                Click the link in that email to set a new password. The link expires in 30 minutes. Don't forget to check your spam folder.
              </p>
            </div>

            <div className="mt-8 space-y-3">
              <Link
                to="/login"
                className="block w-full text-center bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90 transition"
              >
                Back to Login
              </Link>
              <button
                type="button"
                onClick={resend}
                className="w-full text-sm text-foreground hover:text-primary underline-offset-2 hover:underline"
              >
                Didn't receive it? Resend link
              </button>
              <button
                type="button"
                onClick={() => { setSent(false); setEmail(""); }}
                className="w-full text-xs text-muted-foreground hover:text-primary"
              >
                Use a different email
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
