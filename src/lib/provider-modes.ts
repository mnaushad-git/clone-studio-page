/**
 * Turns the provider modes reported by GET /api/v1/admin/system/status into the
 * operational notice shown in the Admin Portal. The text is built from the modes the
 * API actually reports, so it stays correct in every deployment (local development,
 * staging with a live staging-Odoo push, production) without hardcoding any of them.
 * Only the mode names ("stub", "live", …) are used — no configuration values.
 */
import type { SystemStatusOut } from "@/lib/admin-api";

export type ProviderModes = Pick<
  SystemStatusOut,
  "payment_provider_mode" | "notification_provider_mode" | "odoo_order_push_mode"
>;

type ProviderKey = keyof ProviderModes;

const PROVIDERS: {
  key: ProviderKey;
  label: string;
  plural: boolean;
  /** What does not happen while this provider is simulated. */
  simulatedEffect: string;
  /** What does happen while this provider is live. */
  liveEffect: string;
}[] = [
  {
    key: "payment_provider_mode",
    label: "payments",
    plural: true,
    simulatedEffect: "charges",
    liveEffect: "customers are really charged",
  },
  {
    key: "odoo_order_push_mode",
    label: "Odoo order push",
    plural: false,
    simulatedEffect: "ERP orders",
    liveEffect: "orders are sent to the connected Odoo",
  },
  {
    key: "notification_provider_mode",
    label: "notifications",
    plural: true,
    simulatedEffect: "emails/SMS",
    liveEffect: "real emails and SMS are sent",
  },
];

export const STUB_MODE = "stub";

function joinList(items: string[], conjunction: string): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} ${conjunction} ${items[items.length - 1]}`;
}

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export type ProviderSummary = {
  /** True when at least one provider is simulated, i.e. the notice should be shown. */
  anySimulated: boolean;
  simulated: string[];
  active: { label: string; mode: string }[];
  message: string;
};

export function summariseProviderModes(modes: ProviderModes): ProviderSummary {
  const simulated = PROVIDERS.filter((p) => modes[p.key] === STUB_MODE);
  const active = PROVIDERS.filter((p) => modes[p.key] !== STUB_MODE);

  const sentences: string[] = [];
  if (simulated.length) {
    const verb = simulated.length > 1 || simulated[0].plural ? "are" : "is";
    sentences.push(
      `${capitalise(joinList(simulated.map((p) => p.label), "and"))} ${verb} simulated — no real ${joinList(
        simulated.map((p) => p.simulatedEffect),
        "or",
      )}.`,
    );
  }
  for (const p of active) {
    const mode = modes[p.key];
    const verb = p.plural ? "are" : "is";
    sentences.push(
      mode === "live"
        ? `${capitalise(p.label)} ${verb} live — ${p.liveEffect}.`
        : `${capitalise(p.label)} mode: ${mode}.`,
    );
  }

  return {
    anySimulated: simulated.length > 0,
    simulated: simulated.map((p) => p.label),
    active: active.map((p) => ({ label: p.label, mode: modes[p.key] })),
    message: `Test mode: ${sentences.join(" ")}`,
  };
}
