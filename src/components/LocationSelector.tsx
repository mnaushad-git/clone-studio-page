import { useEffect, useState } from "react";
import { useRouter } from "@tanstack/react-router";
import { MapPin, X, Check } from "lucide-react";
import { CITIES, FLAGS } from "@/lib/location";
import { location, useStore } from "@/lib/store";

export function LocationSelector() {
  const current = useStore((s) => s.location);
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const isHome = router.state.location.pathname === "/";

  useEffect(() => {
    if (!current && !isHome) {
      const t = setTimeout(() => setOpen(true), 800);
      return () => clearTimeout(t);
    }
  }, [current, isHome]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handler = () => setOpen(true);
    window.addEventListener("tb:open-location", handler);
    return () => window.removeEventListener("tb:open-location", handler);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        <div className="p-6 border-b border-border flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-primary">
              <MapPin className="h-5 w-5" />
              <h2 className="font-display text-xl">Where should we deliver?</h2>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Pick your city to see accurate delivery windows and pricing.
            </p>
          </div>
          {current && (
            <button
              onClick={() => setOpen(false)}
              aria-label="Close"
              className="h-8 w-8 rounded-full hover:bg-muted flex items-center justify-center"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
        <div className="max-h-[60vh] overflow-y-auto">
          {CITIES.map((c) => {
            const selected = current?.slug === c.slug;
            return (
              <button
                key={c.slug}
                onClick={() => {
                  location.set(c);
                  setOpen(false);
                }}
                className={`w-full flex items-center justify-between px-6 py-4 border-b border-border/60 hover:bg-muted/40 transition text-left ${
                  selected ? "bg-primary/5" : ""
                }`}
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{FLAGS[c.countryCode] ?? "🌍"}</span>
                  <div>
                    <div className="font-semibold text-primary">{c.city}</div>
                    <div className="text-xs text-muted-foreground">{c.country} · {c.currency}</div>
                  </div>
                </div>
                {selected && <Check className="h-5 w-5 text-primary" />}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
