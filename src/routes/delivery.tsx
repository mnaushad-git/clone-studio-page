import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import {
  User, ShoppingBag, Check, MapPin, Minus, Plus, Ticket,
  Bike, Truck, Facebook, Instagram, Twitter, Youtube, ChevronDown,
} from "lucide-react";

import sprinkleCake from "@/assets/divine-1.jpg";

export const Route = createFileRoute("/delivery")({
  component: DeliveryPage,
  head: () => ({
    meta: [
      { title: "Delivery Details — Terrific Bites" },
      { name: "description", content: "Enter recipient and delivery details for your Terrific Bites order before continuing to payment." },
      { property: "og:title", content: "Delivery Details — Terrific Bites" },
      { property: "og:description", content: "Add recipient info and delivery address for your Terrific Bites order." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

function DeliveryPage() {
  const [qty, setQty] = useState(1);
  const [promo, setPromo] = useState("");
  const [gift, setGift] = useState(false);
  const [secret, setSecret] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [area, setArea] = useState("");
  const [address, setAddress] = useState("");
  const [extra, setExtra] = useState("");

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
          <Step n={2} label="Delivery Details" active />
          <div className="flex-1 h-px bg-border" />
          <Step n={3} label="Payment" />
        </div>

        <div className="grid lg:grid-cols-[1fr_400px] gap-6">
          {/* Left form */}
          <section className="bg-white rounded-2xl shadow-sm p-6">
            <div className="flex items-start justify-between gap-4">
              <div className="flex gap-3">
                <MapPin className="h-5 w-5 text-primary shrink-0 mt-1" />
                <div>
                  <h2 className="font-semibold">Ask the recipient for The Address</h2>
                  <p className="text-xs text-muted-foreground mt-1 max-w-md">
                    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris in dignissim elit. Fusce
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm">Gift?</span>
                <button
                  onClick={() => setGift(!gift)}
                  className={`w-11 h-6 rounded-full transition relative ${gift ? "bg-primary" : "bg-secondary"}`}
                  aria-label="Toggle gift"
                >
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
                  <input value={phone} onChange={(e) => setPhone(e.target.value)} className="border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary" />
                </div>
              </div>

              <label className="flex items-center justify-between border border-border rounded-md px-4 py-3 cursor-pointer">
                <span className="text-sm">Keep my identity secret</span>
                <input type="checkbox" checked={secret} onChange={(e) => setSecret(e.target.checked)} className="h-4 w-4 accent-primary" />
              </label>

              {!gift && (
                <>
                  {/* Map */}
                  <div className="relative rounded-lg overflow-hidden border border-border h-56 bg-secondary">
                    <img
                      src="https://maps.googleapis.com/maps/api/staticmap?center=Cambridge,UK&zoom=12&size=800x400&maptype=roadmap"
                      alt="Map"
                      className="w-full h-full object-cover opacity-90"
                      onError={(e) => ((e.currentTarget.style.display = "none"))}
                    />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <button className="bg-primary text-primary-foreground rounded-md px-6 py-3 text-sm shadow-lg">
                        Change Location
                      </button>
                    </div>
                    <div className="absolute top-2 left-2 bg-white rounded shadow text-[11px] flex">
                      <span className="px-2 py-1 border-r border-border">Map</span>
                      <span className="px-2 py-1">Satellite</span>
                    </div>
                  </div>

                  <Field label="Recipient Area" required>
                    <div className="relative">
                      <select
                        value={area}
                        onChange={(e) => setArea(e.target.value)}
                        className="w-full appearance-none border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-white"
                      >
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

                  <Field label="Extra Address" required>
                    <input
                      value={extra}
                      onChange={(e) => setExtra(e.target.value)}
                      placeholder="Extra address details (opational)"
                      className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary placeholder:text-muted-foreground"
                    />
                  </Field>
                </>
              )}
            </div>
          </section>

          {gift && (
            <section className="bg-white rounded-2xl shadow-sm p-6">
              <div className="flex items-center gap-2 mb-5">
                <Bike className="h-5 w-5 text-primary" />
                <h2 className="font-semibold">Delivery time</h2>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setTimeSlot("tomorrow")}
                  className={`rounded-xl border p-5 text-center transition ${
                    timeSlot === "tomorrow"
                      ? "border-primary bg-[oklch(0.95_0.03_20)]"
                      : "border-border hover:border-primary"
                  }`}
                >
                  <p className="font-semibold">Delivery time</p>
                  <p className="text-sm mt-2">Tomorrow</p>
                  <p className="text-xs text-muted-foreground mt-1">10:00am - 2:00pm</p>
                </button>
                <button
                  onClick={() => setTimeSlot("another")}
                  className={`rounded-xl border p-5 text-center transition ${
                    timeSlot === "another"
                      ? "border-primary bg-[oklch(0.95_0.03_20)]"
                      : "border-border hover:border-primary"
                  }`}
                >
                  <p className="font-semibold">Another time</p>
                  <p className="text-xs text-muted-foreground mt-2">Choose another<br />date and time</p>
                </button>
              </div>
            </section>
          )}

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

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm mb-2">{label} {required && <span className="text-primary">*</span>}</label>
      {children}
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
