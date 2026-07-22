import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { ChevronDown, ChevronRight, ShoppingBag, User, Facebook, Instagram, Twitter, Youtube, Minus, Plus, Cake } from "lucide-react";

import main from "@/assets/cake-main.jpg";
import t2 from "@/assets/cake-thumb-2.jpg";
import t3 from "@/assets/cake-thumb-3.jpg";
import t4 from "@/assets/cake-thumb-4.jpg";
import r1 from "@/assets/rel-1.jpg";
import r2 from "@/assets/rel-2.jpg";
import r3 from "@/assets/rel-3.jpg";
import r4 from "@/assets/rel-4.jpg";

export const Route = createFileRoute("/product")({
  component: ProductPage,
  head: () => ({
    meta: [
      { title: "Sprinkle Cupcakes — Buttercream Cake | Terrific Bites" },
      { name: "description", content: "Order our signature buttercream sprinkle cake — three luscious layers, custom inscription, vanilla or chocolate." },
      { property: "og:title", content: "Buttercream Sprinkle Cake — Terrific Bites" },
      { property: "og:description", content: "Three-layer buttercream cake finished with rainbow sprinkles and a cherry on top." },
      { property: "og:type", content: "product" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const thumbs = [main, t2, t3, t4];
const sizes = [
  { label: "6 INCH", sub: "3 Layers" },
  { label: "9 INCH", sub: "3 Layers" },
];
const flavors = ["Vanilla", "Chocolate"];
const tabs = ["Description", "Storage Instructions", "Ingredients", "Allergens"];
const related = [r1, r2, r3, r4];

function ProductPage() {
  const [active, setActive] = useState(0);
  const [size, setSize] = useState(1);
  const [flavor, setFlavor] = useState(0);
  const [qty, setQty] = useState(1);
  const [tab, setTab] = useState(2);
  const [inscription, setInscription] = useState("");

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-2 text-muted-foreground uppercase">
        Order Desserts for Local Pickup
      </div>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      {/* Header */}
      <header className="bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-lg">🇺🇸</span><span>English</span><ChevronDown className="h-3 w-3" />
          </div>
          <Link to="/" className="font-script text-3xl text-primary leading-none text-center">
            Terrific<br /><span className="ml-6">Bites</span>
          </Link>
          <div className="flex items-center gap-6 text-sm">
            <button className="flex items-center gap-2"><User className="h-4 w-4" /> My Account</button>
            <button className="flex items-center gap-2"><ShoppingBag className="h-4 w-4" /> Cart</button>
          </div>
        </div>
      </header>

      {/* Breadcrumbs */}
      <div className="max-w-7xl mx-auto px-6 pt-8">
        <nav className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-3 w-3" />
          <span>Happy Birthday</span>
          <ChevronRight className="h-3 w-3" />
          <span className="text-primary">Sprinkle Cupcakes</span>
        </nav>
      </div>

      {/* Product */}
      <section className="max-w-7xl mx-auto px-6 pt-6 pb-16 grid md:grid-cols-2 gap-12">
        {/* Gallery */}
        <div>
          <div className="bg-secondary rounded-md overflow-hidden aspect-square flex items-center justify-center">
            <img src={thumbs[active]} alt="Buttercream Cake" width={900} height={900} className="w-full h-full object-cover" />
          </div>
          <div className="mt-4 grid grid-cols-4 gap-3">
            {thumbs.map((t, i) => (
              <button key={i} onClick={() => setActive(i)} className={`aspect-square rounded-md overflow-hidden border ${active === i ? "border-primary" : "border-border"}`}>
                <img src={t} alt="thumbnail" loading="lazy" width={200} height={200} className="w-full h-full object-cover" />
              </button>
            ))}
          </div>
        </div>

        {/* Info */}
        <div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-3xl font-bold text-foreground">$300</div>
              <div className="text-xs text-muted-foreground mt-1">All prices include VAT</div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-2 justify-end text-sm">
                <Cake className="h-4 w-4 text-primary" />
                <span className="font-semibold">Earn 1234</span>
              </div>
              <a href="#" className="text-xs underline text-muted-foreground">Terrific points</a>
            </div>
          </div>

          <h1 className="mt-6 font-display text-3xl text-primary">Buttercream Cake</h1>

          {/* Size */}
          <div className="mt-6 grid grid-cols-2 gap-3">
            {sizes.map((s, i) => (
              <button key={i} onClick={() => setSize(i)} className={`flex items-center gap-3 border rounded-md p-3 text-left ${size === i ? "border-primary" : "border-border"}`}>
                <span className={`h-4 w-4 rounded-full border ${size === i ? "border-primary" : "border-muted-foreground/50"} flex items-center justify-center`}>
                  {size === i && <span className="h-2 w-2 rounded-full bg-primary" />}
                </span>
                <span>
                  <span className="block text-sm font-semibold">{s.label}</span>
                  <span className="block text-[11px] text-muted-foreground uppercase tracking-wider">{s.sub}</span>
                </span>
              </button>
            ))}
          </div>

          {/* Flavor */}
          <div className="mt-3 grid grid-cols-2 gap-3">
            {flavors.map((f, i) => (
              <button key={f} onClick={() => setFlavor(i)} className={`flex items-center gap-3 border rounded-md p-3 uppercase text-sm ${flavor === i ? "border-primary" : "border-border"}`}>
                <span className={`h-4 w-4 rounded-full border ${flavor === i ? "border-primary" : "border-muted-foreground/50"} flex items-center justify-center`}>
                  {flavor === i && <span className="h-2 w-2 rounded-full bg-primary" />}
                </span>
                {f}
              </button>
            ))}
          </div>

          {/* Qty + Add to cart */}
          <div className="mt-6 grid grid-cols-[auto_1fr] gap-3">
            <div className="flex items-center border border-border rounded-md">
              <button onClick={() => setQty(Math.max(1, qty - 1))} className="p-3"><Minus className="h-4 w-4" /></button>
              <span className="w-10 text-center">{qty}</span>
              <button onClick={() => setQty(qty + 1)} className="p-3"><Plus className="h-4 w-4" /></button>
            </div>
            <button className="bg-foreground text-background rounded-md font-semibold hover:opacity-90">Add To Cart</button>
          </div>
          <button className="mt-3 w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90">Buy Now</button>

          {/* Inscription */}
          <div className="mt-6">
            <div className="flex items-center justify-between border-b border-border pb-2 text-sm text-muted-foreground">
              <input value={inscription} onChange={(e) => setInscription(e.target.value.slice(0, 22))} placeholder="Add Custom Inscription" className="bg-transparent outline-none flex-1" />
              <span>{inscription.length}/22</span>
            </div>
            <div className="flex items-center justify-between border-b border-border pb-2 text-sm mt-4">
              <span>Select Inscription Color: <span className="text-foreground">White</span></span>
              <ChevronDown className="h-4 w-4" />
            </div>
          </div>

          {/* Ways to pay */}
          <div className="mt-6 border border-border rounded-md p-4">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold">Ways to pay</h4>
              <div className="flex items-center gap-2">
                {["VISA", "PayPal", "APay", "MC"].map(p => (
                  <span key={p} className="bg-secondary text-foreground rounded px-2 py-1 text-[10px] font-semibold">{p}</span>
                ))}
              </div>
            </div>
            {[1, 2].map(i => (
              <div key={i} className="mt-3 flex items-center justify-between border-t border-border pt-3">
                <div>
                  <div className="text-sm">Pay in installments with valU!</div>
                  <a href="#" className="text-xs underline text-muted-foreground">Learn more</a>
                </div>
                <span className="bg-gradient-to-r from-orange-400 to-pink-500 text-white rounded px-3 py-1 text-xs font-bold">SONiC</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tabs */}
      <section className="max-w-7xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-2 md:grid-cols-4 border-b border-border">
          {tabs.map((t, i) => (
            <button key={t} onClick={() => setTab(i)} className={`py-4 text-sm ${tab === i ? "text-foreground border-b-2 border-foreground font-semibold" : "text-muted-foreground"}`}>{t}</button>
          ))}
        </div>
        <div className="pt-8 max-w-4xl">
          <h3 className="font-semibold mb-4">Worem ipsum dolor sit amet consectetur.</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Classic Banana Pudding Ingredients: Vanilla Pudding (Sweetened Condensed Milk (Milk, Sucrose), Water, Vanilla Pudding Mix (Dextrose, Sugar, Modified Food Starch, Tetrasodium Pyrophosphate, Tricalcium Phosphate, Natural And Artificial Flavor, Salt, Xanthan Gum, Nonfat Dry Milk, Mono And Diglycerides, Yellow 5, Yellow 6), Heavy Cream (Cream, Milk, Carrageenan, Mono And Diglycerides, Cellulose Gum, Polysorbate 80), Bananas, Vanilla Wafers (Enriched Flour (Wheat Flour, Niacin, Reduced Iron, Thiamine Mononitrate, Riboflavin, Folic Acid), Sugar, Interesterified Soybean Oil, Whey (Milk), Dextrose, Salt, Leavening Agents (Sodium Bicarbonate, Monocalcium Phosphate), Artificial Flavors, Egg, Modified Food Starch)
          </p>
          <p className="mt-4 text-sm text-muted-foreground leading-relaxed">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris in dignissim elit. Fusce dictum tristique accumsan. Nulla in rhoncus sapien, eu rutrum diam. Proin nibh tortor, congue nec tellus vitae, ullamcorper pulvinar odio. Morbi lacinia congue molestie. Quisque tristique tellus ac.
          </p>
        </div>
      </section>

      {/* You may also like */}
      <section className="max-w-7xl mx-auto px-6 pb-16">
        <div className="bg-secondary rounded-lg p-8">
          <h2 className="font-display text-2xl text-primary mb-6">You May Also Like</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            {related.map((img, i) => (
              <div key={i}>
                <div className="aspect-square overflow-hidden rounded-md">
                  <img src={img} alt="Sprinkle Cupcakes" loading="lazy" width={500} height={500} className="w-full h-full object-cover hover:scale-105 transition duration-500" />
                </div>
                <h3 className="mt-3 font-display text-primary text-sm">Sprinkle Cupcakes</h3>
                <div className="text-xs text-muted-foreground">$4.5</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "var(--brand)" }} />

      {/* Footer */}
      <footer className="bg-primary text-primary-foreground">
        <div className="max-w-7xl mx-auto px-6 py-14 grid md:grid-cols-4 gap-10">
          <div>
            <div className="w-16 h-16 bg-background rounded-sm flex items-center justify-center font-script text-primary text-lg">TB</div>
            <p className="mt-4 text-xs opacity-80 max-w-xs">Worem ipsum dolor sit amet consectetur adipiscing elit magna pulvinar, pulvinar euismod dolor nascetur sea blandit etiam sed.</p>
            <div className="flex gap-3 mt-5">
              {[Facebook, Instagram, Twitter, Youtube].map((I, i) => (
                <a key={i} href="#" className="h-7 w-7 rounded-full bg-background/10 flex items-center justify-center hover:bg-background/20"><I className="h-3.5 w-3.5" /></a>
              ))}
            </div>
          </div>
          {[
            { title: "Column One", items: ["Twenty One", "Thirty Two", "Fourty Three", "Fifty Four"] },
            { title: "Column Two", items: ["Sixty Five", "Seventy Six", "Eighty Seven", "Ninety Eight"] },
            { title: "Column Three", items: ["One Two", "Three Four", "Five Six", "Seven Eight"] },
          ].map(col => (
            <div key={col.title}>
              <h4 className="font-display uppercase text-sm tracking-wider mb-4">{col.title}</h4>
              <ul className="space-y-2 text-xs opacity-80">
                {col.items.map(i => <li key={i}><a href="#" className="hover:opacity-100">{i}</a></li>)}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-primary-foreground/10">
          <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap justify-between items-center gap-4 text-[11px] opacity-70">
            <span>Copyright © 2024 Example company. All Rights Reserved</span>
            <div className="flex gap-2">
              {["VISA", "AMEX", "PayPal", "GPay"].map(p => (
                <span key={p} className="bg-background text-primary rounded px-2 py-1 text-[10px] font-semibold">{p}</span>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
