import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Check, MapPin, Truck, Bike, Ticket, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { useStore, addresses as addressStore, selectSubtotal, selectDiscount, selectTax, selectDeliveryFee, selectTotal, promo } from "@/lib/store";
import { getProduct } from "@/lib/products";

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
  const subtotal = useStore(selectSubtotal);
  const discount = useStore(selectDiscount);
  const tax = useStore(selectTax);
  const deliveryFee = useStore(selectDeliveryFee);
  const total = useStore(selectTotal);

  const [gift, setGift] = useState(false);
  const [secret, setSecret] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [area, setArea] = useState("");
  const [address, setAddress] = useState("");
  const [extra, setExtra] = useState("");
  const [timeSlot, setTimeSlot] = useState<"tomorrow" | "another">("tomorrow");
  const [promoInput, setPromoInput] = useState(currentPromo?.code ?? "");

  const applyPromo = () => {
    if (!promoInput.trim()) return;
    if (promo.apply(promoInput)) toast.success("Promo code applied");
    else toast.error("Invalid promo code");
  };

  const submit = () => {
    if (!name.trim()) return toast.error("Recipient name is required");
    if (!phone.trim()) return toast.error("Recipient phone is required");
    if (!gift && (!area || !address.trim())) return toast.error("Please add a delivery address");

    addressStore.add({
      name,
      phone: `+966 ${phone}`,
      area: gift ? "Gift" : area,
      address: gift ? `Delivery: ${timeSlot}` : address,
      extra: extra || undefined,
      isGift: gift,
      identitySecret: secret,
      timeSlot: gift ? timeSlot : undefined,
    });
    toast.success("Delivery details saved");
    navigate({ to: "/payment" });
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        <div className="bg-white rounded-2xl shadow-sm px-8 py-5 flex items-center gap-4 mb-6">
          <Step n={1} label="Customize" done />
          <div className="flex-1 h-px bg-border" />
          <Step n={2} label="Delivery Details" active />
          <div className="flex-1 h-px bg-border" />
          <Step n={3} label="Payment" />
        </div>

        <div className="grid lg:grid-cols-[1fr_400px] gap-6">
          <section className="bg-white rounded-2xl shadow-sm p-6">
            <div className="flex items-start justify-between gap-4">
              <div className="flex gap-3">
                <MapPin className="h-5 w-5 text-primary shrink-0 mt-1" />
                <div>
                  <h2 className="font-semibold">Recipient & Delivery</h2>
                  <p className="text-xs text-muted-foreground mt-1 max-w-md">
                    Tell us where to deliver. Sending a gift? Toggle the switch and we'll pick a time slot.
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
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
                <div className="grid grid-cols-[180px_1fr] gap-3">
                  <button type="button" className="border border-border rounded-md px-3 py-3 text-sm flex items-center justify-between">
                    Saudi Arabia (+966) <ChevronDown className="h-4 w-4" />
                  </button>
                  <input value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 15))} className="border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary" />
                </div>
              </div>

              <label className="flex items-center justify-between border border-border rounded-md px-4 py-3 cursor-pointer">
                <span className="text-sm">Keep my identity secret</span>
                <input type="checkbox" checked={secret} onChange={(e) => setSecret(e.target.checked)} className="h-4 w-4 accent-primary" />
              </label>

              {!gift ? (
                <>
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

                  <Field label="Recipient Area" required>
                    <div className="relative">
                      <select value={area} onChange={(e) => setArea(e.target.value)} className="w-full appearance-none border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-white">
                        <option value="">Select area</option>
                        <option>Riyadh</option>
                        <option>Jeddah</option>
                        <option>Dammam</option>
                      </select>
                      <ChevronDown className="h-4 w-4 absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
                    </div>
                  </Field>

                  <Field label="Recipient Address" required>
                    <input value={address} onChange={(e) => setAddress(e.target.value)} className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary" />
                  </Field>

                  <Field label="Extra Address">
                    <input value={extra} onChange={(e) => setExtra(e.target.value)} placeholder="Apartment, floor, landmark (optional)" className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary placeholder:text-muted-foreground" />
                  </Field>
                </>
              ) : (
                <div className="mt-2">
                  <div className="flex items-center gap-2 mb-3">
                    <Bike className="h-5 w-5 text-primary" />
                    <h3 className="font-semibold">Delivery time</h3>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <button onClick={() => setTimeSlot("tomorrow")} className={`rounded-xl border p-5 text-center transition ${timeSlot === "tomorrow" ? "border-primary bg-[oklch(0.95_0.03_20)]" : "border-border hover:border-primary"}`}>
                      <p className="font-semibold">Tomorrow</p>
                      <p className="text-xs text-muted-foreground mt-1">10:00am – 2:00pm</p>
                    </button>
                    <button onClick={() => setTimeSlot("another")} className={`rounded-xl border p-5 text-center transition ${timeSlot === "another" ? "border-primary bg-[oklch(0.95_0.03_20)]" : "border-border hover:border-primary"}`}>
                      <p className="font-semibold">Another time</p>
                      <p className="text-xs text-muted-foreground mt-1">Choose date & time</p>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </section>

          <aside className="space-y-4">
            <div className="bg-white rounded-2xl shadow-sm p-5">
              <div className="flex items-center gap-3">
                <Bike className="h-8 w-8 text-primary shrink-0" />
                <p className="text-sm font-medium flex-1">
                  {subtotal - discount >= 200 ? "You've unlocked free delivery! 🎉" : `Only $${(200 - (subtotal - discount)).toFixed(2)} to Go for Free Delivery!`}
                </p>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${Math.min(100, ((subtotal - discount) / 200) * 100)}%` }} />
                </div>
                <span className="text-xs text-muted-foreground">$200</span>
              </div>
            </div>

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
                      <p className="text-sm font-semibold">${(it.unitPrice * it.qty).toFixed(2)}</p>
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
                <Row label="Subtotal" val={`$${subtotal.toFixed(2)}`} />
                {discount > 0 && <Row label={`Discount`} val={`-$${discount.toFixed(2)}`} />}
                <Row label="Delivery" val={deliveryFee === 0 ? "Free" : `$${deliveryFee.toFixed(2)}`} />
                <Row label="Tax" val={`$${tax.toFixed(2)}`} />
                <div className="flex items-center gap-2 text-xs text-foreground/80 pt-2">
                  <Truck className="h-3.5 w-3.5" /> Skinniy Express
                </div>
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <span className="font-semibold">Order Total</span>
                <span className="font-semibold text-lg">${total.toFixed(2)}</span>
              </div>
            </div>

            <button onClick={submit} disabled={cartItems.length === 0} className="w-full bg-primary text-primary-foreground rounded-md py-4 font-semibold hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed">
              Continue to Payment
            </button>
          </aside>
        </div>
      </main>

      <SiteFooter />
    </div>
  );
}

function Step({ n, label, active, done }: { n: number; label: string; active?: boolean; done?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className={`h-9 w-9 rounded-full flex items-center justify-center text-sm font-semibold ${
        done ? "bg-[oklch(0.85_0.08_120)] text-primary" : active ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground"
      }`}>
        {done ? <Check className="h-4 w-4" /> : n}
      </div>
      <span className={`text-sm ${active || done ? "font-semibold" : "text-muted-foreground"}`}>{label}</span>
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
