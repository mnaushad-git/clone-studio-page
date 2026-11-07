import { DEMO_MODE } from "@/lib/demo";
import { useT } from "@/lib/i18n";

/** Shown on every page of a demo build, including the Admin Portal. */
export function DemoBanner() {
  const t = useT();
  if (!DEMO_MODE) return null;
  return (
    <div
      role="status"
      data-testid="demo-banner"
      className="bg-amber-500 text-black text-center text-xs py-2 px-4 font-medium"
    >
      {t("demoBanner")}
    </div>
  );
}

export function DemoPaymentNotice() {
  const t = useT();
  return (
    <section
      data-testid="demo-payment-notice"
      className="bg-amber-50 border border-amber-300 rounded-2xl p-6 space-y-1"
    >
      <h2 className="font-semibold">{t("demoPaymentTitle")}</h2>
      <p className="text-sm">{t("demoPaymentDesc")}</p>
    </section>
  );
}

/** Driven by the order's own is_demo flag from the backend, not by the build flag. */
export function DemoOrderNotice() {
  const t = useT();
  return (
    <div
      role="status"
      data-testid="demo-order-notice"
      className="max-w-3xl mx-auto mt-6 px-6 py-3 bg-amber-50 border border-amber-300 rounded-md text-sm font-medium text-center"
    >
      {t("demoOrderNotice")}
    </div>
  );
}

export function DemoSignInNotice() {
  const t = useT();
  if (!DEMO_MODE) return null;
  return (
    <p
      data-testid="demo-signin-notice"
      className="mb-4 px-3 py-2 bg-amber-50 border border-amber-300 rounded-md text-xs text-center"
    >
      {t("demoSignInNotice")}
    </p>
  );
}
