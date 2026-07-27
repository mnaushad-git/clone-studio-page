import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Check, MapPin, Truck, Bike, Ticket, ChevronDown, ChevronLeft, ChevronRight, X, CalendarPlus } from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { useStore, addresses as addressStore, selectSubtotal, selectDiscount, selectTax, selectDeliveryFee, selectTotal, promo, RIYADH_AREAS, type Address } from "@/lib/store";
import { getAdminState } from "@/lib/admin-store";
import { getProduct } from "@/lib/products";

const DAY_SLOTS: [number, number][] = [[8, 10], [10, 12], [12, 14], [14, 16], [16, 18], [18, 20]];
const fmtHour = (h: number) => {
  const period = h >= 12 && h < 24 ? "pm" : "am";
  const hh = h % 12 === 0 ? 12 : h % 12;
  return `${hh}:00${period}`;
};
function toMin(s: string) { const [h, m] = s.split(":").map(Number); return (h || 0) * 60 + (m || 0); }
function fmtLabel(from: string, to: string) {
  const h1 = parseInt(from.split(":")[0] || "0", 10);
  const h2 = parseInt(to.split(":")[0] || "0", 10);
  return `${fmtHour(h1)} - ${fmtHour(h2)}`;
}
function slotSource(): { label: string; startMin: number }[] {
  const admin = getAdminState().slots.filter((s) => s.active);
  if (admin.length) return admin.map((s) => ({ label: s.label || fmtLabel(s.from, s.to), startMin: toMin(s.from) }));
  return DAY_SLOTS.map(([s, e]) => ({ label: `${fmtHour(s)} - ${fmtHour(e)}`, startMin: s * 60 }));
}
export function getSlotLabels(): string[] { return slotSource().map((s) => s.label); }
export const SLOT_LABELS = getSlotLabels();
function nextSlot(now = new Date()): { day: "Today" | "Tomorrow"; label: string } {
  const src = slotSource();
  const mins = now.getHours() * 60 + now.getMinutes();
  const idx = src.findIndex((s) => s.startMin > mins);
  if (idx >= 0) return { day: "Today", label: src[idx].label };
  return { day: "Tomorrow", label: src[0]?.label ?? "" };
}

export const Route = createFileRoute("/delivery")({
  component: DeliveryPage,
  head: () => ({
    meta: [
      { title: "Delivery Details — Terrific Bites" },
      { name: "description", content: "Enter recipient and delivery details for your Terrific Bites order." },
      { property: "og:title", content: "Delivery Details — Terrific Bites" },
      { property: "og:description", content: "Add recipient info and delivery address." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

function DeliveryPage() {
  const navigate = useNavigate();
  const cartItems = useStore((s) => s.cart);
  const currentPromo = useStore((s) => s.promo);
  const user = useStore((s) => s.user);
  const savedAddresses = useStore((s) => s.addresses);
  const subtotal = useStore(selectSubtotal);
  const discount = useStore(selectDiscount);
  const tax = useStore(selectTax);
  const deliveryFee = useStore(selectDeliveryFee);
  const total = useStore(selectTotal);

  const defaultSlot = useMemo(() => nextSlot(), []);

  const [gift, setGift] = useState(false);
  const [identitySecret, setIdentitySecret] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [area, setArea] = useState("");
  const [address, setAddress] = useState("");
  const [extra, setExtra] = useState("");
  const [selectedAddressId, setSelectedAddressId] = useState<string | null>(null);
  const [addressModalOpen, setAddressModalOpen] = useState(false);
  const [timeSlot, setTimeSlot] = useState<"tomorrow" | "another">("tomorrow");
  const [promoInput, setPromoInput] = useState(currentPromo?.code ?? "");
  const [timeModalOpen, setTimeModalOpen] = useState(false);
  const [pickedDate, setPickedDate] = useState<string>("");
  const [pickedTime, setPickedTime] = useState<string>("");

  const selfAddresses = useMemo(() => savedAddresses.filter((a) => !a.isGift), [savedAddresses]);

  const applyAddress = (id: string) => {
    const a = selfAddresses.find((x) => x.id === id);
    if (!a) return;
    setSelectedAddressId(a.id);
    if (a.name) setName(a.name);
    if (a.phone) setPhone(a.phone.replace(/^\+966\s?/, ""));
    setArea(a.area || "");
    setAddress(a.address || "");
    setExtra(a.extra || "");
  };

  // When gift toggle is off, prefill from user profile + default (or latest) self address
  useEffect(() => {
    if (gift) return;
    const def = selfAddresses.find((a) => a.isDefault) ?? selfAddresses[selfAddresses.length - 1];
    if (user?.name) setName(user.name);
    else if (def?.name) setName(def.name);
    if (user?.phone) setPhone(user.phone.replace(/^\+966\s?/, ""));
    else if (def?.phone) setPhone(def.phone.replace(/^\+966\s?/, ""));
    if (def) {
      setSelectedAddressId(def.id);
      setArea(def.area || "");
      setAddress(def.address || "");
      setExtra(def.extra || "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gift]);

  const applyPromo = () => {
    if (!promoInput.trim()) return;
    if (promo.apply(promoInput)) toast.success("Promo code applied");
    else toast.error("Invalid promo code");
  };

  const submit = () => {
    if (!name.trim()) return toast.error("Recipient name is required");
    if (!phone.trim()) return toast.error("Recipient phone is required");
    if (!gift && (!area || !address.trim())) return toast.error("Please add a delivery address");
    if (timeSlot === "another" && (!pickedDate || !pickedTime)) return toast.error("Please pick a delivery date and time");

    const deliveryDate = timeSlot === "tomorrow" ? defaultSlot.day : pickedDate;
    const deliveryTime = timeSlot === "tomorrow" ? defaultSlot.label : pickedTime;

    if (gift || !selectedAddressId) {
      addressStore.add({
        name,
        phone: phone.startsWith("+966") ? phone : `+966 ${phone}`,
        area: gift ? "Gift" : area,
        address: gift ? `${deliveryDate} · ${deliveryTime}` : address,
        extra: extra || undefined,
        isGift: gift,
        identitySecret: gift ? identitySecret : undefined,
        timeSlot,
        deliveryDate,
        deliveryTime,
      });
    }
    toast.success("Delivery details saved");
    navigate({ to: "/payment" });
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="bg-white rounded-2xl shadow-sm px-3 sm:px-8 py-4 sm:py-5 flex items-center gap-2 sm:gap-4 mb-6">
          <Step n={1} label="Customize" done />
          <div className="flex-1 h-px bg-border" />
          <Step n={2} label="Delivery Details" active />
          <div className="flex-1 h-px bg-border" />
          <Step n={3} label="Payment" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
          <section className="bg-white rounded-2xl shadow-sm p-4 sm:p-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex gap-3 min-w-0">
                <MapPin className="h-5 w-5 text-primary shrink-0 mt-1" />
                <div className="min-w-0">
                  <h2 className="font-semibold">Recipient & Delivery</h2>
                  <p className="text-xs text-muted-foreground mt-1">
                    Tell us where to deliver. Sending a gift? Toggle the switch and we'll pick a time slot.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-sm">Gift?</span>
                <button onClick={() => setGift(!gift)} className={`w-11 h-6 rounded-full transition relative ${gift ? "bg-primary" : "bg-secondary"}`} aria-label="Toggle gift">
                  <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition ${gift ? "left-5" : "left-0.5"}`} />
                </button>
              </div>
            </div>

            <div className="mt-6 space-y-5">
              <Field label="Recipient name" required>
                <input value={name} onChange={(e) => setName(e.target.value)} className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary" />
              </Field>

              <div>
                <label className="block text-sm mb-2">Recipient phone <span className="text-primary">*</span></label>
                <div className="grid grid-cols-1 sm:grid-cols-[180px_minmax(0,1fr)] gap-3">
                  <button type="button" className="border border-border rounded-md px-3 py-3 text-sm flex items-center justify-between">
                    <span className="truncate">Saudi Arabia (+966)</span> <ChevronDown className="h-4 w-4 shrink-0" />
                  </button>
                  <input value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 15))} className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary" />
                </div>
              </div>

              {!gift && (
                <>
                  {selfAddresses.length > 0 && (
                    <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 px-4 py-3">
                      <div className="min-w-0">
                        <p className="text-xs text-muted-foreground">Delivering to</p>
                        <p className="text-sm font-medium truncate">
                          {area ? `${area} — ${address || "—"}` : "No address selected"}
                        </p>
                      </div>
                      <button type="button" onClick={() => setAddressModalOpen(true)} className="text-sm text-primary font-medium hover:underline shrink-0 ml-3">
                        Change address
                      </button>
                    </div>
                  )}
                  <div className="relative rounded-lg overflow-hidden border border-border h-56 bg-secondary flex items-center justify-center">
                    <div className="text-center">
                      <MapPin className="h-8 w-8 mx-auto text-primary" />
                      <p className="text-xs text-muted-foreground mt-2">Interactive map preview</p>
                      <p className="text-sm font-medium mt-1">{area || "Select an area"}{address && ` — ${address}`}</p>
                    </div>
                    <div className="absolute top-2 left-2 bg-white rounded shadow text-[11px] flex">
                      <span className="px-2 py-1 border-r border-border">Map</span>
                      <span className="px-2 py-1">Satellite</span>
                    </div>
                  </div>

                  <Field label="Riyadh Area" required>
                    <div className="relative">
                      <select value={area} onChange={(e) => setArea(e.target.value)} className="w-full appearance-none border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-white">
                        <option value="">Select a Riyadh area</option>
                        {RIYADH_AREAS.map((a) => <option key={a} value={a}>{a}</option>)}
                      </select>
                      <ChevronDown className="h-4 w-4 absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                    </div>
                  </Field>

                  <Field label="Address" required>
                    <input value={address} onChange={(e) => setAddress(e.target.value)} className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary" />
                  </Field>

                  <Field label="Extra Address">
                    <input value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="Apartment, floor, landmark (optional)" className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary placeholder:text-muted-foreground" />
                  </Field>
                </>
              )}
              {gift && (
                <label className="flex items-start gap-3 rounded-lg border border-border p-3 cursor-pointer hover:border-primary transition">
                  <input
                    type="checkbox"
                    checked={identitySecret}
                    onChange={(e) => setIdentitySecret(e.target.checked)}
                    className="mt-0.5 h-4 w-4 accent-primary"
                  />
                  <span className="text-sm">
                    <span className="font-medium">Keep my identity secret</span>
                    <span className="block text-xs text-muted-foreground mt-0.5">The recipient won't see who sent the gift.</span>
                  </span>
                </label>
              )}


              <div className="mt-2">
                <div className="flex items-center gap-2 mb-3">
                  <Bike className="h-5 w-5 text-primary" />
                  <h3 className="font-semibold">Delivery time</h3>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <button onClick={() => setTimeSlot("tomorrow")} className={`rounded-xl border p-5 text-center transition ${timeSlot === "tomorrow" ? "border-primary bg-[oklch(0.95_0.03_20)]" : "border-border hover:border-primary"}`}>
                    <p className="font-semibold">{defaultSlot.day}</p>
                    <p className="text-xs text-muted-foreground mt-1">{defaultSlot.label}</p>
                  </button>
                  <button onClick={() => { setTimeSlot("another"); setTimeModalOpen(true); }} className={`rounded-xl border p-5 text-center transition ${timeSlot === "another" ? "border-primary bg-[oklch(0.95_0.03_20)]" : "border-border hover:border-primary"}`}>
                    <p className="font-semibold">Another time</p>
                    <p className="text-xs text-muted-foreground mt-1">{timeSlot === "another" && pickedDate && pickedTime ? `${pickedDate} · ${pickedTime}` : "Choose date & time"}</p>
                  </button>
                </div>
              </div>
            </div>
          </section>

          <aside className="space-y-4">
            {cartItems.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
                <p className="text-sm text-muted-foreground">Your cart is empty.</p>
                <Link to="/chocolates" className="mt-3 inline-block text-sm text-primary underline">Continue shopping</Link>
              </div>
            ) : (
              <div className="bg-white rounded-2xl shadow-sm p-5 space-y-3 max-h-72 overflow-y-auto">
                {cartItems.map((it) => {
                  const p = getProduct(it.productId);
                  return (
                    <div key={it.lineId} className="flex gap-3 items-center">
                      <img src={p?.image} alt={p?.name} className="w-14 h-14 rounded-md object-cover" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{p?.name}</p>
                        <p className="text-xs text-muted-foreground">Qty {it.qty}</p>
                      </div>
                      <p className="text-sm font-semibold">SAR {(it.unitPrice * it.qty).toFixed(2)}</p>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="bg-white rounded-2xl shadow-sm p-3 flex items-center gap-2">
              <div className="flex items-center gap-2 flex-1 px-3">
                <Ticket className="h-4 w-4 text-muted-foreground" />
                <input value={promoInput} onChange={(e) => setPromoInput(e.target.value.toUpperCase())} placeholder="Promo Code" className="flex-1 text-sm outline-none bg-transparent py-2" />
              </div>
              <button onClick={applyPromo} className="bg-[oklch(0.72_0.08_160)] text-white rounded-md px-6 py-2 text-sm hover:opacity-90">Apply</button>
            </div>

            <div className="bg-white rounded-2xl shadow-sm p-5 space-y-4">
              <h3 className="font-semibold">Order Summary</h3>
              <div className="space-y-2 text-sm">
                <Row label="Subtotal" val={`SAR ${subtotal.toFixed(2)}`} />
                {discount > 0 && <Row label={`Discount`} val={`-SAR ${discount.toFixed(2)}`} />}
                <Row label="Delivery" val={deliveryFee === 0 ? "Free" : `SAR ${deliveryFee.toFixed(2)}`} />
                <Row label="Tax" val={`SAR ${tax.toFixed(2)}`} />
                <div className="flex items-center gap-2 text-xs text-foreground/80 pt-2">
                  <Truck className="h-3.5 w-3.5" /> Skinniy Express
                </div>
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <span className="font-semibold">Order Total</span>
                <span className="font-semibold text-lg">SAR {total.toFixed(2)}</span>
              </div>
            </div>

            <button onClick={submit} disabled={cartItems.length === 0} className="w-full bg-primary text-primary-foreground rounded-md py-4 font-semibold hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed">
              Continue to Payment
            </button>
          </aside>
        </div>
      </main>

      {timeModalOpen && (
        <AnotherTimeModal
          initialDate={pickedDate}
          initialTime={pickedTime}
          onClose={() => setTimeModalOpen(false)}
          onConfirm={(d, t) => {
            setPickedDate(d);
            setPickedTime(t);
            setTimeModalOpen(false);
            toast.success("Delivery time selected");
          }}
        />
      )}

      {addressModalOpen && (
        <AddressPickerModal
          addresses={selfAddresses}
          selectedId={selectedAddressId}
          onClose={() => setAddressModalOpen(false)}
          onSelect={(id) => { applyAddress(id); setAddressModalOpen(false); toast.success("Address selected"); }}
          onAdd={(a) => {
            const id = addressStore.add({ ...a, isGift: false });
            applyAddress(id);
            setAddressModalOpen(false);
            toast.success("Address added");
          }}
        />
      )}

      <SiteFooter />
    </div>
  );
}

type Quick = { key: string; label: string; sub: string };

function AnotherTimeModal({ initialDate, initialTime, onClose, onConfirm }: { initialDate: string; initialTime: string; onClose: () => void; onConfirm: (date: string, time: string) => void }) {
  const now = new Date();
  const quickDates = useMemo<Quick[]>(() => {
    const fmt = (d: Date) => d.toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "long" });
    const today = new Date(now);
    const t = new Date(now); t.setDate(t.getDate() + 1);
    const t2 = new Date(now); t2.setDate(t2.getDate() + 2);

    const slots: Quick[] = [];
    // If any same-day slots remain, offer Today as a quick option
    if (DAY_SLOTS.some(([s]) => s > now.getHours())) {
      slots.push({ key: fmt(today), label: "Today", sub: today.toLocaleDateString("en-US", { day: "numeric", month: "long" }) });
    }
    slots.push(
      { key: fmt(t), label: "Tomorrow", sub: t.toLocaleDateString("en-US", { day: "numeric", month: "long" }) },
      { key: fmt(t2), label: t2.toLocaleDateString("en-US", { weekday: "long" }), sub: t2.toLocaleDateString("en-US", { day: "numeric", month: "long" }) },
    );
    return slots;
  }, []);

  const [mode, setMode] = useState<"quick" | "pick">(initialDate && !quickDates.find((q) => q.key === initialDate) ? "pick" : "quick");
  const [date, setDate] = useState<string>(initialDate || quickDates[0].key);
  const [time, setTime] = useState<string>(initialTime);
  const [calMonth, setCalMonth] = useState<Date>(new Date(now.getFullYear(), now.getMonth(), 1));

  const timeSlots = getSlotLabels();
  const todayKey = new Date(now).toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "long" });
  const isTodaySelected = date === todayKey;
  const currentSlotIdx = DAY_SLOTS.findIndex(([s]) => s > now.getHours());

  const monthLabel = calMonth.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  const firstDow = new Date(calMonth.getFullYear(), calMonth.getMonth(), 1).getDay();
  const daysInMonth = new Date(calMonth.getFullYear(), calMonth.getMonth() + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array.from({ length: firstDow }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const pickCalDay = (d: number) => {
    const chosen = new Date(calMonth.getFullYear(), calMonth.getMonth(), d);
    setDate(chosen.toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "long" }));
  };

  const confirm = () => {
    if (!time) return toast.error("Please select a delivery time");
    onConfirm(date, time);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-lg">Another time</h3>
          <button onClick={onClose} aria-label="Close"><X className="h-5 w-5" /></button>
        </div>

        <div className="mt-5">
          <p className="text-sm mb-3">Select Delivery date</p>
          <div className="grid grid-cols-3 gap-3">
            {quickDates.map((q) => (
              <button key={q.key} onClick={() => { setMode("quick"); setDate(q.key); }} className={`rounded-lg p-4 text-center text-sm transition ${mode === "quick" && date === q.key ? "bg-primary text-primary-foreground" : "bg-secondary hover:bg-secondary/70"}`}>
                <p className="font-medium">{q.label}</p>
                <p className="text-xs mt-1 opacity-90">{q.sub}</p>
              </button>
            ))}
            <button onClick={() => setMode("pick")} className={`rounded-lg p-4 text-center text-sm transition flex flex-col items-center justify-center gap-1 ${mode === "pick" ? "bg-primary text-primary-foreground" : "bg-secondary hover:bg-secondary/70"}`}>
              <CalendarPlus className="h-5 w-5" />
              <span className="font-medium">Pick a date</span>
            </button>
          </div>
        </div>

        {mode === "pick" && (
          <div className="mt-5">
            <div className="flex items-center justify-center gap-3 mb-3">
              <button onClick={() => setCalMonth(new Date(calMonth.getFullYear(), calMonth.getMonth() - 1, 1))} className="p-1.5 rounded bg-secondary hover:bg-secondary/70"><ChevronLeft className="h-4 w-4" /></button>
              <span className="font-medium">{monthLabel}</span>
              <button onClick={() => setCalMonth(new Date(calMonth.getFullYear(), calMonth.getMonth() + 1, 1))} className="p-1.5 rounded bg-secondary hover:bg-secondary/70"><ChevronRight className="h-4 w-4" /></button>
            </div>
            <div className="grid grid-cols-7 text-center text-xs text-muted-foreground mb-1">
              {["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map((d) => <div key={d} className="py-1">{d}</div>)}
            </div>
            <div className="grid grid-cols-7 text-center text-sm">
              {cells.map((c, i) => {
                if (c === null) return <div key={i} className="py-2" />;
                const cellDate = new Date(calMonth.getFullYear(), calMonth.getMonth(), c);
                const key = cellDate.toLocaleDateString("en-US", { weekday: "long", day: "numeric", month: "long" });
                const isPast = cellDate < new Date(now.getFullYear(), now.getMonth(), now.getDate());
                const selected = key === date;
                return (
                  <button
                    key={i}
                    disabled={isPast}
                    onClick={() => pickCalDay(c)}
                    className={`py-2 m-0.5 rounded transition ${selected ? "bg-[oklch(0.72_0.08_160)] text-white" : isPast ? "text-muted-foreground/50 cursor-not-allowed" : "hover:bg-secondary"}`}
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className="mt-6">
          <p className="text-sm mb-3">Select a Delivery time <span className="text-primary">*</span></p>
          <div className="grid grid-cols-2 gap-3">
            {timeSlots.map((slot, idx) => {
              const isPastSlot = isTodaySelected && idx < currentSlotIdx;
              return (
                <button key={slot} onClick={() => !isPastSlot && setTime(slot)} disabled={isPastSlot} className={`text-center rounded-lg border px-4 py-3 text-sm transition ${time === slot ? "border-primary bg-[oklch(0.95_0.03_20)]" : "border-border hover:border-primary"} ${isPastSlot ? "opacity-50 cursor-not-allowed" : ""}`}>
                  {slot}
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-6 flex items-center gap-3">
          <button onClick={onClose} className="px-6 py-2.5 rounded-md border border-border text-sm hover:bg-secondary">Cancel</button>
          <button onClick={confirm} className="px-6 py-2.5 rounded-md bg-primary text-primary-foreground text-sm hover:opacity-90">Confirm</button>
        </div>
      </div>
    </div>
  );
}

function Step({ n, label, active, done }: { n: number; label: string; active?: boolean; done?: boolean }) {
  return (
    <div className="flex items-center gap-2 sm:gap-3 min-w-0">
      <div className={`h-8 w-8 sm:h-9 sm:w-9 shrink-0 rounded-full flex items-center justify-center text-sm font-semibold ${
        done ? "bg-[oklch(0.85_0.08_120)] text-primary" : active ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground"
      }`}>
        {done ? <Check className="h-4 w-4" /> : n}
      </div>
      <span className={`hidden sm:inline text-sm truncate ${active || done ? "font-semibold" : "text-muted-foreground"}`}>{label}</span>
      {active && <span className="sm:hidden text-xs font-semibold truncate">{label}</span>}
    </div>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm mb-2">{label} {required && <span className="text-primary">*</span>}</label>
      {children}
    </div>
  );
}

function Row({ label, val }: { label: string; val: string }) {
  return <div className="flex items-center justify-between"><span>{label}</span><span>{val}</span></div>;
}
