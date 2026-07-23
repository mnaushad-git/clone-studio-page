import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import {
  User, ShoppingBag, Check, MessageSquare, Minus, Plus, Ticket,
  Bike, MapPin, Truck, Facebook, Instagram, Twitter, Youtube, ChevronDown, X,
} from "lucide-react";

import giftCard from "@/assets/gift-card.jpg";
import sprinkleCake from "@/assets/divine-1.jpg";
import extra1 from "@/assets/prod-swiss.jpg";
import extra2 from "@/assets/divine-3.jpg";
import extra3 from "@/assets/prod-butter.jpg";
import popDonut from "@/assets/extra-donut.jpg";
import popIcecream from "@/assets/extra-icecream.jpg";
import popCheesecake from "@/assets/extra-cheesecake.jpg";
import popDonutsPair from "@/assets/extra-donuts-pair.jpg";

const popupExtras = [
  { name: "Fanky Sweets", price: "$ 44.89", img: popDonut },
  { name: "Fanky Sweets", price: "$ 44.89", img: popIcecream },
  { name: "Fanky Sweets", price: "$ 44.89", img: popCheesecake },
  { name: "Fanky Sweets", price: "$ 44.89", img: popDonutsPair },
];

export const Route = createFileRoute("/customize")({
  component: CustomizePage,
  head: () => ({
    meta: [
      { title: "Customize Your Order — Terrific Bites" },
      { name: "description", content: "Personalize your Terrific Bites order — add a gift card, custom message and extras, then continue to delivery and payment." },
      { property: "og:title", content: "Customize Your Order — Terrific Bites" },
      { property: "og:description", content: "Add a gift card, message and extras to your Terrific Bites order." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const extras = [
  { name: "Fanky Sweets", code: "EPG 987", img: extra1 },
  { name: "Fanky Sweets", code: "EPG 987", img: extra2 },
  { name: "Fanky Sweets", code: "EPG 987", img: extra3 },
];

function CustomizePage() {
  const [qty, setQty] = useState(1);
  const [promo, setPromo] = useState("");
  const [showExtras, setShowExtras] = useState(false);
  const [selected, setSelected] = useState<number[]>([]);
  const toggle = (i: number) =>
    setSelected((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i]));
  const total = selected.length * 44.89 + 1187.55;

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Announcement */}
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-3 uppercase">
        Order Desserts for Local Pickup
      </div>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      {/* Nav */}
      <header className="bg-background">
        <div className="max-w-7xl mx-auto px-6 py-5 grid grid-cols-3 items-center">
          <button className="flex items-center gap-2 text-sm justify-self-start">
            <span className="text-lg">🇺🇸</span> English <ChevronDown className="h-4 w-4" />
          </button>
          <Link to="/" className="font-script text-3xl text-primary leading-none justify-self-center text-center">
            Terrific<br /><span className="ml-6">Bites</span>
          </Link>
          <div className="flex items-center gap-6 text-sm justify-self-end text-primary">
            <button className="flex items-center gap-2"><User className="h-5 w-5" /> My Account</button>
            <button className="flex items-center gap-2"><ShoppingBag className="h-5 w-5" /> Cart</button>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {/* Steps */}
        <div className="bg-white rounded-2xl shadow-sm px-8 py-5 flex items-center gap-4 mb-6">
          <Step n={1} label="Customize" active done />
          <div className="flex-1 h-px bg-border" />
          <Step n={2} label="Delivery Details" />
          <div className="flex-1 h-px bg-border" />
          <Step n={3} label="Payment" />
        </div>

        <div className="grid lg:grid-cols-[1fr_400px] gap-6">
          {/* Left column */}
          <div className="space-y-6">
            {/* Gift card & message */}
            <section className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5 text-primary" />
                  <h2 className="font-semibold">Gift Card & Message</h2>
                </div>
                <button className="bg-primary text-primary-foreground rounded-md px-6 py-2 text-sm hover:opacity-90 transition">
                  Customize
                </button>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <button className="group">
                  <div className="aspect-square rounded-lg overflow-hidden border-2 border-dashed border-border">
                    <img src={giftCard} alt="Gift card" width={600} height={600} loading="lazy" className="w-full h-full object-cover" />
                  </div>
                  <p className="text-center text-sm mt-3">Select Gift Card</p>
                </button>
                <button className="group">
                  <div className="aspect-square rounded-lg border-2 border-dashed border-border flex flex-col items-center justify-center gap-3 text-muted-foreground">
                    <MessageSquare className="h-6 w-6" />
                    <span className="text-sm">Tap to add message</span>
                  </div>
                  <p className="text-center text-sm mt-3">Add Message</p>
                </button>
              </div>
            </section>

            {/* Extras */}
            <section className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-semibold">Add a Little Extra for a Special Touch!</h2>
                <button onClick={() => setShowExtras(true)} className="text-sm text-primary hover:underline">View All</button>
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
            {/* Free delivery bar */}
            <div className="bg-white rounded-2xl shadow-sm p-5">
              <div className="flex items-center gap-3">
                <Bike className="h-8 w-8 text-primary shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium">Only EGP 101 to Go for Free Delivery!</p>
                </div>
              </div>
              <div className="mt-3 flex items-center gap-3">
                <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full w-1/2 bg-primary rounded-full" />
                </div>
                <span className="text-xs text-muted-foreground">USD 101</span>
              </div>
            </div>

            {/* Cart item */}
            <div className="bg-white rounded-2xl shadow-sm p-5">
              <div className="flex gap-4">
                <img src={sprinkleCake} alt="Sprinkle Cupcakes" width={200} height={200} loading="lazy" className="w-24 h-24 rounded-lg object-cover" />
                <div className="flex-1">
                  <h3 className="font-display text-primary">Sprinkle Cupcakes</h3>
                  <p className="text-xs text-muted-foreground mt-1">2 Count Pack</p>
                  <p className="text-xs text-muted-foreground">Delivery: Local</p>
                  <div className="flex items-center justify-between mt-3">
                    <div className="flex items-center border border-border rounded-md">
                      <button onClick={() => setQty(Math.max(1, qty - 1))} className="px-2 py-1 hover:text-primary"><Minus className="h-3 w-3" /></button>
                      <span className="px-3 text-sm">{qty}</span>
                      <button onClick={() => setQty(qty + 1)} className="px-2 py-1 hover:text-primary"><Plus className="h-3 w-3" /></button>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between mt-3">
                <p className="font-semibold">$1200.5</p>
                <button className="text-xs text-primary underline">Remove</button>
              </div>
            </div>

            {/* Promo */}
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
              <button className="bg-[oklch(0.72_0.08_160)] text-white rounded-md px-6 py-2 text-sm hover:opacity-90 transition">
                Apply
              </button>
            </div>

            {/* Order summary */}
            <div className="bg-white rounded-2xl shadow-sm p-5 space-y-4">
              <h3 className="font-semibold">Order Summary</h3>
              <div className="space-y-2 text-sm">
                <Row label={`X${qty}  Sprinkle Cupcakes`} val={`$${(1187.55).toFixed(2)}`} />
                {selected.map((i) => (
                  <Row key={i} label={`X1  ${popupExtras[i].name}`} val={popupExtras[i].price} />
                ))}
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
                <Row label="Amount" val={`$${total.toFixed(2)}`} />
                <Row label="Tax" val="$12.99" />
              </div>
              <div className="border-t border-border pt-4 flex items-center justify-between">
                <span className="font-semibold">Order Total</span>
                <span className="font-semibold">${(total + 12.99).toFixed(2)}</span>
              </div>
            </div>

            <button className="w-full bg-primary text-primary-foreground rounded-md py-4 font-semibold hover:opacity-90 transition">
              Continue to Delivery
            </button>
          </aside>
        </div>
      </main>

      {/* Extras popup */}
      {showExtras && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-start justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-5xl mt-16 p-8 relative">
            <button
              onClick={() => setShowExtras(false)}
              aria-label="Close"
              className="absolute top-5 right-5 text-primary hover:opacity-70"
            >
              <X className="h-5 w-5" />
            </button>
            <h3 className="text-lg font-semibold">Add a Little Extra for a Special Touch!</h3>
            <p className="text-sm text-muted-foreground mt-1">Worem ipsum dolor sit amet, consectetur adipiscing elit.</p>
            <div className="mt-6 border-t border-border" />
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              {popupExtras.map((p, i) => {
                const isSel = selected.includes(i);
                return (
                  <div key={i} className={`bg-secondary/40 rounded-xl p-3 ${isSel ? "ring-2 ring-primary" : ""}`}>
                    <div className="aspect-square rounded-lg overflow-hidden bg-white">
                      <img src={p.img} alt={p.name} width={600} height={600} loading="lazy" className="w-full h-full object-cover" />
                    </div>
                    <p className="text-center text-sm font-medium mt-3">{p.name}</p>
                    <p className="text-center text-sm mt-1">{p.price}</p>
                    <button
                      onClick={() => toggle(i)}
                      className={`mt-3 w-full border rounded-md py-2 text-sm transition ${
                        isSel
                          ? "bg-primary text-primary-foreground border-primary"
                          : "border-primary text-primary hover:bg-primary hover:text-primary-foreground"
                      }`}
                    >
                      {isSel ? "Added" : "Shop now"}
                    </button>
                  </div>
                );
              })}
            </div>
            <div className="mt-8 flex items-center justify-between border-t border-border pt-6">
              <div className="flex items-center gap-3 text-sm">
                <span className="text-muted-foreground">Total Price</span>
                <span className="font-semibold text-base">${total.toFixed(2)}</span>
                <span className="text-muted-foreground text-xs">All prices include tax</span>
              </div>
              <button
                onClick={() => setShowExtras(false)}
                className="bg-primary text-primary-foreground rounded-md px-8 py-3 text-sm hover:opacity-90 transition"
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Zigzag divider */}
      <div className="h-10" style={{ background: "oklch(0.9 0.05 20)", clipPath: "polygon(0 100%, 5% 0, 10% 100%, 15% 0, 20% 100%, 25% 0, 30% 100%, 35% 0, 40% 100%, 45% 0, 50% 100%, 55% 0, 60% 100%, 65% 0, 70% 100%, 75% 0, 80% 100%, 85% 0, 90% 100%, 95% 0, 100% 100%)" }} />

      {/* Footer */}
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
          done
            ? "bg-[oklch(0.85_0.08_120)] text-primary"
            : active
            ? "bg-primary text-primary-foreground"
            : "bg-secondary text-foreground"
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
