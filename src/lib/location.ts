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

export function nextDeliveryWindow(city: { sameDayCutoffHour: number } | null) {
  const now = new Date();
  const cutoff = city?.sameDayCutoffHour ?? 15;
  const hoursRemaining = cutoff - now.getHours() - now.getMinutes() / 60;
  if (hoursRemaining > 0) {
    const h = Math.floor(hoursRemaining);
    const m = Math.floor((hoursRemaining - h) * 60);
    return { sameDay: true, hoursRemaining, label: `Order in ${h}h ${m}m for same-day delivery`, short: `${h}h ${m}m left today` };
  }
  return { sameDay: false, hoursRemaining: 0, label: "Next-day delivery available", short: "Next-day delivery" };
}
