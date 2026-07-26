import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { toast } from "sonner";
import { Check, MapPin, Truck, Loader2, Lock } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import {
  useStore, orders, selectSubtotal, selectDiscount, selectTax,
  selectDeliveryFee, selectTotal,
} from "@/lib/store";
import { getProduct } from "@/lib/products";

export const Route = createFileRoute("/payment")({
  component: PaymentPage,
  head: () => ({
    meta: [
      { title: "Payment — Terrific Bites" },
      { name: "description", content: "Complete your Terrific Bites order securely." },
      { property: "og:title", content: "Payment — Terrific Bites" },
      { property: "og:description", content: "Complete your order with your preferred payment method." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const methods = [
  { id: "apple", label: "Apple Pay", type: "apple" as const },
  { id: "credit", label: "Credit Card", type: "mc" as const },
  { id: "paypal", label: "PayPal", type: "paypal" as const },
  { id: "visa", label: "Visa Card", type: "visa" as const },
];

function BrandBadge({ type }: { type: "apple" | "mc" | "paypal" | "visa" }) {
  const base = "h-7 w-10 rounded flex items-center justify-center text-[10px] font-bold";
  if (type === "apple") return <span className={`${base} bg-black text-white`}> Pay</span>;
  if (type === "mc") return (
    <span className={`${base} bg-white border border-border relative`}>
      <span className="absolute left-1.5 h-4 w-4 rounded-full bg-[#eb001b]" />
      <span className="absolute right-1.5 h-4 w-4 rounded-full bg-[#f79e1b] mix-blend-multiply" />
    </span>
  );
  if (type === "paypal") return <span className={`${base} bg-white border border-border text-[#003087] italic`}>Pay<span className="text-[#009cde]">Pal</span></span>;
  return <span className={`${base} bg-white border border-border text-[#1a1f71]`}>VISA</span>;
}

const cardSchema = z.object({
  name: z.string().trim().min(2, "Enter the name on card").max(80),
  number: z.string().transform((v) => v.replace(/\s+/g, "")).pipe(z.string().regex(/^\d{13,19}$/, "Card number must be 13–19 digits")),
  expiry: z.string().regex(/^(0[1-9]|1[0-2])\/\d{2}$/, "Use MM/YY"),
  cvc: z.string().regex(/^\d{3,4}$/, "CVC must be 3–4 digits"),
});

function PaymentPage() {
  const navigate = useNavigate();
  const cartItems = useStore((s) => s.cart);
  const currentPromo = useStore((s) => s.promo);
  const addressList = useStore((s) => s.addresses);
  const subtotal = useStore(selectSubtotal);
  const discount = useStore(selectDiscount);
  const tax = useStore(selectTax);
  const deliveryFee = useStore(selectDeliveryFee);
  const total = useStore(selectTotal);

  const lastAddress = addressList[addressList.length - 1] ?? null;

  const [selected, setSelected] = useState("apple");
  const [card, setCard] = useState({ name: "", number: "", expiry: "", cvc: "" });
  const [errors, setErrors] = useState<Partial<Record<keyof typeof card, string>>>({});
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setErrors({});
    if (cartItems.length === 0) { toast.error("Your cart is empty"); return; }
    if (!selected) { toast.error("Please choose a payment method"); return; }
    let methodLabel = methods.find((m) => m.id === selected)?.label ?? "Payment";
    if (selected === "credit") {
      const parsed = cardSchema.safeParse(card);
      if (!parsed.success) {
        const fieldErrors: Partial<Record<keyof typeof card, string>> = {};
        for (const issue of parsed.error.issues) {
          const key = issue.path[0] as keyof typeof card;
          if (!fieldErrors[key]) fieldErrors[key] = issue.message;
        }
        setErrors(fieldErrors);
        toast.error("Please fix the highlighted fields");
        return;
      }
      methodLabel = `Credit Card •••• ${card.number.replace(/\s/g, "").slice(-4)}`;
    }
    setLoading(true);
    try {
      await new Promise((r) => setTimeout(r, 1200));
      orders.place({ address: lastAddress, method: methodLabel });
      toast.success("Payment confirmed! Your order is on its way.");
      setTimeout(() => navigate({ to: "/success" }), 400);
    } finally {
      setLoading(false);
    }
  };

  const formatCardNumber = (v: string) => v.replace(/\D/g, "").slice(0, 19).replace(/(.{4})/g, "$1 ").trim();
  const formatExpiry = (v: string) => {
    const d = v.replace(/\D/g, "").slice(0, 4);
    return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="bg-white rounded-2xl shadow-sm px-3 sm:px-8 py-4 sm:py-5 flex items-center gap-2 sm:gap-4 mb-6">
          <Step n={1} label="Customize" done />
          <div className="flex-1 h-px bg-border" />
          <Step n={2} label="Delivery Details" done />
          <div className="flex-1 h-px bg-border" />
          <Step n={3} label="Payment" active />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
          <div className="space-y-6">
            <section className="bg-white rounded-2xl shadow-sm p-6 space-y-3">
              {methods.map((m) => {
                const isSel = selected === m.id;
                return (
                  <label key={m.id} className={`flex items-center gap-4 border rounded-xl px-5 py-4 cursor-pointer transition ${isSel ? "border-primary" : "border-border hover:border-primary/60"}`}>
                    <BrandBadge type={m.type} />
                    <span className="flex-1 text-sm font-medium">{m.label}</span>
                    <span className={`h-5 w-5 rounded-full border-2 flex items-center justify-center ${isSel ? "border-primary" : "border-border"}`}>
                      {isSel && <span className="h-2.5 w-2.5 rounded-full bg-primary" />}
                    </span>
                    <input type="radio" name="method" checked={isSel} onChange={() => setSelected(m.id)} className="sr-only" />
                  </label>
                );
              })}
            </section>

            {selected === "credit" && (
              <section className="bg-white rounded-2xl shadow-sm p-6 space-y-4">
                <h2 className="font-semibold">Card details</h2>
                <div>
                  <label className="text-xs text-muted-foreground">Name on card</label>
                  <input value={card.name} onChange={(e) => setCard({ ...card, name: e.target.value })} maxLength={80} className={`mt-1 w-full border rounded-md px-3 py-2 text-sm outline-none focus:border-primary ${errors.name ? "border-destructive" : "border-border"}`} placeholder="Full name" />
                  {errors.name && <p className="mt-1 text-xs text-destructive">{errors.name}</p>}
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Card number</label>
                  <input inputMode="numeric" value={card.number} onChange={(e) => setCard({ ...card, number: formatCardNumber(e.target.value) })} className={`mt-1 w-full border rounded-md px-3 py-2 text-sm outline-none focus:border-primary ${errors.number ? "border-destructive" : "border-border"}`} placeholder="1234 5678 9012 3456" />
                  {errors.number && <p className="mt-1 text-xs text-destructive">{errors.number}</p>}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-muted-foreground">Expiry (MM/YY)</label>
                    <input inputMode="numeric" value={card.expiry} onChange={(e) => setCard({ ...card, expiry: formatExpiry(e.target.value) })} className={`mt-1 w-full border rounded-md px-3 py-2 text-sm outline-none focus:border-primary ${errors.expiry ? "border-destructive" : "border-border"}`} placeholder="MM/YY" />
                    {errors.expiry && <p className="mt-1 text-xs text-destructive">{errors.expiry}</p>}
                  </div>
                  <div>
                    <label className="text-xs text-muted-foreground">CVC</label>
                    <input inputMode="numeric" value={card.cvc} onChange={(e) => setCard({ ...card, cvc: e.target.value.replace(/\D/g, "").slice(0, 4) })} className={`mt-1 w-full border rounded-md px-3 py-2 text-sm outline-none focus:border-primary ${errors.cvc ? "border-destructive" : "border-border"}`} placeholder="123" />
                    {errors.cvc && <p className="mt-1 text-xs text-destructive">{errors.cvc}</p>}
                  </div>
                </div>
              </section>
            )}
          </div>

          <aside className="space-y-4">
            {lastAddress && (
              <div className="bg-white rounded-2xl shadow-sm p-5">
                <h3 className="font-semibold text-sm mb-2 flex items-center gap-2"><MapPin className="h-4 w-4 text-primary" /> Delivering to</h3>
                <p className="text-sm">{lastAddress.name}</p>
                <p className="text-xs text-muted-foreground">{lastAddress.phone}</p>
                <p className="text-xs text-muted-foreground">{lastAddress.address}{lastAddress.extra ? `, ${lastAddress.extra}` : ""}</p>
                <Link to="/delivery" className="text-xs text-primary underline mt-2 inline-block">Change</Link>
              </div>
            )}

            {cartItems.length === 0 ? (
              <div className="bg-white rounded-2xl shadow-sm p-8 text-center">
                <p className="text-sm text-muted-foreground">Your cart is empty.</p>
                <Link to="/chocolates" className="mt-3 inline-block text-sm text-primary underline">Continue shopping</Link>
              </div>
            ) : (
              <div className="bg-white rounded-2xl shadow-sm p-5 space-y-3 max-h-64 overflow-y-auto">
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

            <div className="bg-white rounded-2xl shadow-sm p-5 space-y-3 text-sm">
              <h3 className="font-semibold">Order Summary</h3>
              <Row label="Subtotal" val={`SAR ${subtotal.toFixed(2)}`} />
              {discount > 0 && <Row label={`Discount (${currentPromo?.code})`} val={`-SAR ${discount.toFixed(2)}`} />}
              <Row label="Delivery" val={deliveryFee === 0 ? "Free" : `SAR ${deliveryFee.toFixed(2)}`} />
              <Row label="Tax" val={`SAR ${tax.toFixed(2)}`} />
              <div className="flex items-center gap-2 text-xs text-foreground/80 pt-1">
                <Truck className="h-3.5 w-3.5" /> Skinniy Express
              </div>
              <div className="border-t border-border pt-3 flex items-center justify-between">
                <span className="font-semibold">Order Total</span>
                <span className="font-semibold text-lg">SAR {total.toFixed(2)}</span>
              </div>
            </div>

            <button type="button" onClick={handleConfirm} disabled={loading || cartItems.length === 0}
              className="w-full bg-primary text-primary-foreground rounded-md py-4 font-semibold hover:opacity-90 transition inline-flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed">
              {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Processing…</>
                : <><Lock className="h-4 w-4" /> Confirm payment · SAR {total.toFixed(2)}</>}
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

function Row({ label, val }: { label: string; val: string }) {
  return <div className="flex items-center justify-between"><span>{label}</span><span>{val}</span></div>;
}
