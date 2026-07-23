import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { toast } from "sonner";
import {
  User, ShoppingBag, Check, MapPin, Minus, Plus, Ticket,
  Bike, Truck, Facebook, Instagram, Twitter, Youtube, ChevronDown, Loader2, Lock,
} from "lucide-react";


import sprinkleCake from "@/assets/divine-1.jpg";
import extra1 from "@/assets/prod-swiss.jpg";
import extra2 from "@/assets/divine-3.jpg";
import extra3 from "@/assets/prod-butter.jpg";

export const Route = createFileRoute("/payment")({
  component: PaymentPage,
  head: () => ({
    meta: [
      { title: "Payment — Terrific Bites" },
      { name: "description", content: "Choose your payment method and complete your Terrific Bites order securely." },
      { property: "og:title", content: "Payment — Terrific Bites" },
      { property: "og:description", content: "Complete your Terrific Bites order with your preferred payment method." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const methods = [
  { id: "apple", label: "Pay", badge: "\uF8FF Pay", type: "apple" as const },
  { id: "credit", label: "Credit Card", type: "mc" as const },
  { id: "paypal", label: "PayPal Card", type: "paypal" as const },
  { id: "visa1", label: "Visa  Card", type: "visa" as const },
  { id: "visa2", label: "Visa  Card", type: "visa" as const },
  { id: "visa3", label: "Visa  Card", type: "visa" as const },
];

const extras = [
  { name: "Fanky Sweets", code: "EPG 987", img: extra1 },
  { name: "Fanky Sweets", code: "EPG 987", img: extra2 },
  { name: "Fanky Sweets", code: "EPG 987", img: extra3 },
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
  number: z.string().transform((v) => v.replace(/\s+/g, ""))
    .pipe(z.string().regex(/^\d{13,19}$/, "Card number must be 13–19 digits")),
  expiry: z.string().regex(/^(0[1-9]|1[0-2])\/\d{2}$/, "Use MM/YY"),
  cvc: z.string().regex(/^\d{3,4}$/, "CVC must be 3–4 digits"),
});

function PaymentPage() {
  const navigate = useNavigate();
  const [qty, setQty] = useState(1);
  const [promo, setPromo] = useState("");
  const [selected, setSelected] = useState("apple");
  const [card, setCard] = useState({ name: "", number: "", expiry: "", cvc: "" });
  const [errors, setErrors] = useState<Partial<Record<keyof typeof card, string>>>({});
  const [loading, setLoading] = useState(false);

  const handleConfirm = async () => {
    setErrors({});
    if (!selected) {
      toast.error("Please choose a payment method");
      return;
    }
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
    }
    setLoading(true);
    try {
      await new Promise((r) => setTimeout(r, 1500));
      toast.success("Payment confirmed! Your order is on its way.");
      setTimeout(() => navigate({ to: "/" }), 900);
    } finally {
      setLoading(false);
    }
  };

  const formatCardNumber = (v: string) =>
    v.replace(/\D/g, "").slice(0, 19).replace(/(.{4})/g, "$1 ").trim();
  const formatExpiry = (v: string) => {
    const d = v.replace(/\D/g, "").slice(0, 4);
    return d.length > 2 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
  };


  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-3 uppercase">
        Order Desserts for Local Pickup
      </div>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      <header className="bg-background">
        <div className="max-w-7xl mx-auto px-6 py-5 grid grid-cols-3 items-center">
          <button className="flex items-center gap-2 text-sm justify-self-start">
            <span className="text-lg">🇺🇸</span> English <ChevronDown className="h-4 w-4" />
          </button>
          <Link to="/" className="font-script text-3xl text-primary leading-none justify-self-center text-center">
            Terrific<br /><span className="ml-6">Bites</span>
          </Link>
          <div className="flex items-center gap-6 text-sm justify-self-end text-primary">
            <Link to="/account" className="flex items-center gap-2"><User className="h-5 w-5" /> My Account</Link>
            <button className="flex items-center gap-2"><ShoppingBag className="h-5 w-5" /> Cart</button>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {/* Steps */}
        <div className="bg-white rounded-2xl shadow-sm px-8 py-5 flex items-center gap-4 mb-6">
          <Step n={1} label="Customize" done />
          <div className="flex-1 h-px bg-border" />
          <Step n={2} label="Delivery Details" done />
          <div className="flex-1 h-px bg-border" />
          <Step n={3} label="Payment" active />
        </div>

        <div className="grid lg:grid-cols-[1fr_400px] gap-6">
          <div className="space-y-6">
            {/* Methods */}
            <section className="bg-white rounded-2xl shadow-sm p-6 space-y-3">
              {methods.map((m) => {
                const isSel = selected === m.id;
                return (
                  <label
                    key={m.id}
                    className={`flex items-center gap-4 border rounded-xl px-5 py-4 cursor-pointer transition ${
                      isSel ? "border-primary" : "border-border hover:border-primary/60"
                    }`}
                  >
                    <BrandBadge type={m.type} />
                    <span className="flex-1 text-sm font-medium">{m.label}</span>
                    <span
                      className={`h-5 w-5 rounded-full border-2 flex items-center justify-center ${
                        isSel ? "border-primary" : "border-border"
                      }`}
                    >
                      {isSel && <span className="h-2.5 w-2.5 rounded-full bg-primary" />}
                    </span>
                    <input
                      type="radio"
                      name="method"
                      checked={isSel}
                      onChange={() => setSelected(m.id)}
                      className="sr-only"
                    />
                  </label>
                );
              })}
            </section>

            {/* Extras */}
            <section className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-semibold">Add a Little Extra for a Special Touch!</h2>
                <Link to="/customize" className="text-sm text-primary hover:underline">View All</Link>
              </div>
              <div className="grid grid-cols-3 gap-4">
                {extras.map((e, i) => (
                  <div key={i} className="text-center">
                    <div className="aspect-square rounded-full overflow-hidden bg-secondary">
                      <img src={e.img} alt={e.name} width={400} height={400} loading="lazy" className="w-full h-full object-cover" />
                    </div>
                    <p className="mt-3 text-sm font-medium">{e.name}</p>
                    <p className="text-xs text-muted-foreground">{e.code}</p>
                    <button className="mt-3 w-full border border-border rounded-md py-2 text-sm hover:border-primary hover:text-primary transition">
                      Add
                    </button>
                  </div>
                ))}
              </div>
            </section>
          </div>

          {/* Right column */}
          <aside className="space-y-4">
            <div className="bg-white rounded-2xl shadow-sm p-5">
              <div className="flex items-center gap-3">
                <Bike className="h-8 w-8 text-primary shrink-0" />
                <p className="text-sm font-medium flex-1">Only EGP 101 to Go for Free Delivery!</p>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full w-1/2 bg-primary rounded-full" />
                </div>
                <span className="text-xs text-muted-foreground">USD 101</span>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-sm p-5">
              <div className="flex gap-4">
                <img src={sprinkleCake} alt="Sprinkle Cupcakes" className="w-24 h-24 rounded-lg object-cover" />
                <div className="flex-1">
                  <h3 className="font-display text-primary">Sprinkle Cupcakes</h3>
                  <p className="text-xs text-muted-foreground mt-1">2 Count Pack</p>
                  <p className="text-xs text-muted-foreground">Delivery: Local</p>
                  <div className="flex items-center justify-between mt-3">
                    <div className="flex items-center border border-border rounded-md">
                      <button onClick={() => setQty(Math.max(1, qty - 1))} className="px-2 py-1"><Minus className="h-3 w-3" /></button>
                      <span className="px-3 text-sm">{qty}</span>
                      <button onClick={() => setQty(qty + 1)} className="px-2 py-1"><Plus className="h-3 w-3" /></button>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between mt-3">
                <p className="font-semibold">$1200.5</p>
                <button className="text-xs text-primary underline">Remove</button>
              </div>
            </div>

            <div className="bg-white rounded-2xl shadow-sm p-3 flex items-center gap-2">
              <div className="flex items-center gap-2 flex-1 px-3">
                <Ticket className="h-4 w-4 text-muted-foreground" />
                <input
                  value={promo}
                  onChange={(e) => setPromo(e.target.value)}
                  placeholder="Add Promo Code"
                  className="flex-1 text-sm outline-none bg-transparent py-2"
                />
              </div>
              <button className="bg-[oklch(0.72_0.08_160)] text-white rounded-md px-6 py-2 text-sm hover:opacity-90">
                Apply
              </button>
            </div>

            <div className="bg-white rounded-2xl shadow-sm p-5 space-y-4">
              <h3 className="font-semibold">Order Summary</h3>
              <div className="space-y-2 text-sm">
                <Row label="X1  Sprinkle Cupcakes" val="$90.99" />
                <Row label="X2  Sprinkle Cupcakes" val="$80.99" />
                <Row label="X3  Sprinkle Cupcakes" val="$80.99" />
              </div>
              <div className="border-t border-border pt-4 space-y-2 text-sm">
                <Row label="Delivery today with" val="$360.99" bold />
                <div className="flex items-center gap-2 text-xs text-foreground/80">
                  <Truck className="h-3.5 w-3.5" /> Skinniy Express
                </div>
                <div className="flex items-center gap-2 text-xs text-foreground/80">
                  <MapPin className="h-3.5 w-3.5" /> Deliver to <span className="font-semibold">Jakart, Candada</span>
                </div>
              </div>
              <div className="border-t border-border pt-4 space-y-2 text-sm">
                <Row label="Amount" val="$360.99" />
                <Row label="Tax" val="$12.99" />
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <span className="font-semibold">Order Total</span>
                <span className="font-semibold">$400.99</span>
              </div>
            </div>

            <button className="w-full bg-primary text-primary-foreground rounded-md py-4 font-semibold hover:opacity-90 transition">
              Continue to Payment
            </button>
          </aside>
        </div>
      </main>

      <div className="h-10" style={{ background: "oklch(0.9 0.05 20)", clipPath: "polygon(0 100%, 5% 0, 10% 100%, 15% 0, 20% 100%, 25% 0, 30% 100%, 35% 0, 40% 100%, 45% 0, 50% 100%, 55% 0, 60% 100%, 65% 0, 70% 100%, 75% 0, 80% 100%, 85% 0, 90% 100%, 95% 0, 100% 100%)" }} />

      <footer className="bg-primary text-primary-foreground">
        <div className="max-w-7xl mx-auto px-6 py-14 grid md:grid-cols-4 gap-10">
          <div>
            <div className="w-16 h-16 bg-background rounded-sm flex items-center justify-center font-script text-primary text-lg">TB</div>
            <p className="mt-4 text-xs opacity-80 max-w-xs">Worem ipsum dolor sit amet consectetur adipiscing elit magna pulvinar, conubia nascetur sed blandit etiam est.</p>
            <div className="flex gap-3 mt-5">
              {[Facebook, Twitter, Instagram, Youtube].map((I, i) => (
                <a key={i} href="#" aria-label="social" className="h-7 w-7 rounded-full bg-primary-foreground/10 flex items-center justify-center hover:bg-primary-foreground/20">
                  <I className="h-3.5 w-3.5" />
                </a>
              ))}
            </div>
          </div>
          {[
            { t: "Column One", l: ["Twenty One", "Thirty Two", "Fourty Three", "Fifty Four"] },
            { t: "Column Two", l: ["Sixty Five", "Seventy Six", "Eighty Seven", "Ninety Eight"] },
            { t: "Column Three", l: ["One Two", "Three Four", "Five Six", "Seven Eight"] },
          ].map((c) => (
            <div key={c.t}>
              <h4 className="font-display text-lg mb-4">{c.t}</h4>
              <ul className="space-y-3 text-sm opacity-90">
                {c.l.map((li) => <li key={li}><a href="#" className="hover:opacity-100">{li}</a></li>)}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-primary-foreground/15">
          <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between text-xs opacity-80">
            <span>Copyright © 2024 Example company. All Rights Reserved</span>
            <div className="flex gap-2">
              {["VISA", "PayPal", "Pay", "MC"].map((p) => (
                <span key={p} className="bg-primary-foreground text-primary rounded px-2 py-1 text-[10px] font-semibold">{p}</span>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Step({ n, label, active, done }: { n: number; label: string; active?: boolean; done?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`h-9 w-9 rounded-full flex items-center justify-center text-sm font-semibold ${
          done ? "bg-[oklch(0.85_0.08_120)] text-primary" : active ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground"
        }`}
      >
        {done ? <Check className="h-4 w-4" /> : n}
      </div>
      <span className={`text-sm ${active || done ? "font-semibold" : "text-muted-foreground"}`}>{label}</span>
    </div>
  );
}

function Row({ label, val, bold }: { label: string; val: string; bold?: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className={bold ? "font-semibold" : ""}>{label}</span>
      <span className={bold ? "font-semibold" : ""}>{val}</span>
    </div>
  );
}
