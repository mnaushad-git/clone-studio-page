import { useEffect, useState } from "react";
import { Clock, Truck } from "lucide-react";
import { useStore } from "@/lib/store";
import { nextDeliveryWindow } from "@/lib/location";

export function DeliveryCountdown({ variant = "chip" }: { variant?: "chip" | "banner" }) {
  const city = useStore((s) => s.location);
  const [, setTick] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 60_000);
    return () => clearInterval(t);
  }, []);

  const w = nextDeliveryWindow(city);

  if (variant === "chip") {
    return (
      <span className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider px-2 py-1 rounded ${w.sameDay ? "bg-green-50 text-green-700" : "bg-amber-50 text-amber-700"}`}>
        <Clock className="h-3 w-3" />
        {w.sameDay ? "Same-day" : "Next-day"}
      </span>
    );
  }

  return (
    <div className={`rounded-lg px-4 py-3 flex items-center gap-3 text-sm ${w.sameDay ? "bg-green-50 text-green-800" : "bg-amber-50 text-amber-800"}`}>
      <Truck className="h-5 w-5 flex-shrink-0" />
      <div>
        <div className="font-semibold">{w.label}</div>
        {city && <div className="text-xs opacity-80">Delivering to {city.city}, {city.country}</div>}
      </div>
    </div>
  );
}
