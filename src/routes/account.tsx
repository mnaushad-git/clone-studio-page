import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import {
  User, ShoppingBag, UserRound, MapPin, ShoppingCart, DollarSign,
  FileText, Calendar, Heart, Wallet, Plus,
  Facebook, Instagram, Twitter, Youtube,
} from "lucide-react";

export const Route = createFileRoute("/account")({
  component: AccountPage,
  head: () => ({
    meta: [
      { title: "My Account — Terrific Bites" },
      { name: "description", content: "Manage your Terrific Bites profile, addresses, orders, subscriptions, invoices, favorites and wallet from your account dashboard." },
      { property: "og:title", content: "My Account — Terrific Bites" },
      { property: "og:description", content: "Manage your profile, addresses, orders and rewards at Terrific Bites." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const menu = [
  { key: "personal", label: "My Personal Information", icon: UserRound },
  { key: "address", label: "My Address", icon: MapPin },
  { key: "orders", label: "My Orders", icon: ShoppingCart },
  { key: "subs", label: "My Subscriptions", icon: DollarSign },
  { key: "invoices", label: "Invoices", icon: FileText },
  { key: "occasions", label: "My Occasions", icon: Calendar },
  { key: "addresses", label: "My Addresses", icon: MapPin },
  { key: "favorite", label: "Favorite", icon: Heart },
  { key: "wallet", label: "Terrific Wallet", icon: Wallet },
] as const;

type MenuKey = typeof menu[number]["key"];

function AccountPage() {
  const [active, setActive] = useState<MenuKey>("address");

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Announcement */}
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-3 text-foreground uppercase">
        Order Desserts for Local Pickup
      </div>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      {/* Nav */}
      <header className="bg-background">
        <div className="max-w-7xl mx-auto px-6 py-5 grid grid-cols-3 items-center">
          <button className="flex items-center gap-2 text-sm text-primary justify-self-start">
            <User className="h-5 w-5" /> My Account
          </button>
          <Link to="/" className="font-script text-3xl text-primary leading-none justify-self-center text-center">
            Terrific<br /><span className="ml-6">Bites</span>
          </Link>
          <button className="flex items-center gap-2 text-sm text-primary justify-self-end">
            <ShoppingBag className="h-5 w-5" /> Cart
          </button>
        </div>
        <div className="border-t border-border/60" />
      </header>

      {/* Main */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-14">
        <h1 className="font-display text-4xl text-primary text-center mb-10">My Account</h1>

        <div className="grid md:grid-cols-[320px_1fr] gap-6">
          {/* Sidebar */}
          <aside className="bg-white rounded-2xl shadow-sm p-4 h-fit">
            <ul className="space-y-1">
              {menu.map(({ key, label, icon: Icon }) => {
                const isActive = active === key;
                return (
                  <li key={key}>
                    <button
                      onClick={() => setActive(key)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition ${
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-foreground hover:bg-secondary"
                      }`}
                    >
                      <Icon className="h-5 w-5" />
                      <span>{label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </aside>

          {/* Panel */}
          <section className="bg-white rounded-2xl shadow-sm p-8 min-h-[520px]">
            {active === "address" && (
              <>
                <h2 className="text-sm font-semibold mb-4">Recipient details</h2>
                <button className="w-full border border-border rounded-lg py-5 flex items-center justify-center gap-2 text-sm text-foreground hover:border-primary hover:text-primary transition">
                  <Plus className="h-5 w-5" /> Add Address
                </button>
              </>
            )}

            {active === "personal" && (
              <>
                <h2 className="text-sm font-semibold mb-6">Personal details</h2>
                <div className="grid md:grid-cols-2 gap-5">
                  {["Full name", "Email", "Mobile number", "Date of birth"].map((l) => (
                    <div key={l}>
                      <label className="block text-xs font-semibold mb-2">{l}</label>
                      <input className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-transparent" />
                    </div>
                  ))}
                </div>
                <button className="mt-8 bg-primary text-primary-foreground rounded-md px-8 py-3 text-sm">Save Changes</button>
              </>
            )}

            {active !== "address" && active !== "personal" && (
              <div className="h-full flex flex-col items-center justify-center text-center py-24">
                <h2 className="font-display text-2xl text-primary">
                  {menu.find((m) => m.key === active)?.label}
                </h2>
                <p className="text-sm text-muted-foreground mt-3 max-w-sm">
                  Nothing here yet. Your {menu.find((m) => m.key === active)?.label.toLowerCase()} will appear in this space.
                </p>
              </div>
            )}
          </section>
        </div>
      </main>

      {/* Zigzag pink dividers */}
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
