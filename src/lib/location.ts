import type { City } from "./store";

export const CITIES: City[] = [
  { country: "Saudi Arabia", countryCode: "SA", city: "Riyadh", slug: "sa-riyadh", currency: "SAR", sameDayCutoffHour: 15 },
  { country: "Saudi Arabia", countryCode: "SA", city: "Jeddah", slug: "sa-jeddah", currency: "SAR", sameDayCutoffHour: 15 },
  { country: "Saudi Arabia", countryCode: "SA", city: "Dammam", slug: "sa-dammam", currency: "SAR", sameDayCutoffHour: 14 },
  { country: "United Arab Emirates", countryCode: "AE", city: "Dubai", slug: "ae-dubai", currency: "AED", sameDayCutoffHour: 16 },
  { country: "United Arab Emirates", countryCode: "AE", city: "Abu Dhabi", slug: "ae-abudhabi", currency: "AED", sameDayCutoffHour: 15 },
  { country: "Kuwait", countryCode: "KW", city: "Kuwait City", slug: "kw-kuwait", currency: "KWD", sameDayCutoffHour: 15 },
  { country: "Qatar", countryCode: "QA", city: "Doha", slug: "qa-doha", currency: "QAR", sameDayCutoffHour: 15 },
  { country: "Egypt", countryCode: "EG", city: "Cairo", slug: "eg-cairo", currency: "EGP", sameDayCutoffHour: 14 },
];

export const FLAGS: Record<string, string> = {
  SA: "🇸🇦", AE: "🇦🇪", KW: "🇰🇼", QA: "🇶🇦", EG: "🇪🇬",
};

const STORE_TIME_ZONE = "Asia/Riyadh";

/**
 * The current time on the store's clock, as a Date whose local fields read as store time.
 * Delivery slots and the same-day cutoff are about when the bakery can deliver, not what the
 * visitor's device says. It also means the server and the browser agree, whatever time zone
 * each is in, so these labels can't break hydration.
 */
export function storeNow(now: Date = new Date()): Date {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: STORE_TIME_ZONE,
    hourCycle: "h23",
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
  }).formatToParts(now);
  const part = (type: string) => Number(parts.find((p) => p.type === type)?.value);
  return new Date(part("year"), part("month") - 1, part("day"), part("hour"), part("minute"));
}

export function nextDeliveryWindow(city: { sameDayCutoffHour: number } | null) {
  const now = storeNow();
  const cutoff = city?.sameDayCutoffHour ?? 15;
  const hoursRemaining = cutoff - now.getHours() - now.getMinutes() / 60;
  if (hoursRemaining > 0) {
    const h = Math.floor(hoursRemaining);
    const m = Math.floor((hoursRemaining - h) * 60);
    return { sameDay: true, hoursRemaining, label: `Order in ${h}h ${m}m for same-day delivery`, short: `${h}h ${m}m left today` };
  }
  return { sameDay: false, hoursRemaining: 0, label: "Next-day delivery available", short: "Next-day delivery" };
}
