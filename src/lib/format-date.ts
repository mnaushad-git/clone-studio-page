import type { Lang } from "@/lib/i18n";

/** For dates rendered on the server. A fixed locale and time zone give the server and the
 * browser the same text, whatever the visitor's own settings are, so hydration can't break. */
export function formatStableDate(timestamp: number, lang: Lang): string {
  return new Intl.DateTimeFormat(lang === "ar" ? "ar-SA" : "en-US", { timeZone: "UTC" }).format(
    new Date(timestamp),
  );
}
