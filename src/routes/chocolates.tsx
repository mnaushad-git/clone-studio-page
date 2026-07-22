import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronDown, ChevronRight, ShoppingBag, User, Facebook, Instagram, Twitter, Youtube } from "lucide-react";

import c1 from "@/assets/choc-1.jpg";
import c2 from "@/assets/choc-2.jpg";
import c3 from "@/assets/choc-3.jpg";
import c4 from "@/assets/choc-4.jpg";
import c5 from "@/assets/choc-5.jpg";
import c6 from "@/assets/choc-6.jpg";
import c7 from "@/assets/choc-7.jpg";
import c8 from "@/assets/choc-8.jpg";
import c9 from "@/assets/choc-9.jpg";
import prodSwiss from "@/assets/prod-swiss.jpg";
import prodMoose from "@/assets/prod-moose.jpg";
import prodButter from "@/assets/prod-butter.jpg";

export const Route = createFileRoute("/chocolates")({
  component: ChocolatesPage,
  head: () => ({
    meta: [
      { title: "Chocolates — Terrific Bites" },
      { name: "description", content: "Browse our full collection of artisan chocolates, truffles and gift boxes." },
      { property: "og:title", content: "Chocolates — Terrific Bites" },
      { property: "og:description", content: "Browse our full collection of artisan chocolates and gift boxes." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const categories = [
  { name: "Sweets", img: prodSwiss },
  { name: "Chocolates", img: c1 },
  { name: "Happy Birthday", img: prodButter },
  { name: "Sweets", img: prodMoose },
  { name: "Worem ipsum", img: c4 },
  { name: "Worem ipsum", img: c6 },
  { name: "Moose Cream", img: c2 },
];

const products = [c1, c3, c9, c2, c7, c8, c4, c5, c6, c1, c8, c9];

const filterGroups = [
  { title: "Occasions", items: ["Worem ipsum", "Worem ipsum", "Worem ipsum", "Worem ipsum"], more: true },
  { title: "By recipient", items: ["Friends", "Father", "Aunt", "Mom"], more: true },
  { title: "Bundle", items: ["Worem ipsum", "Worem ipsum"] },
  { title: "Color", items: ["White", "Read", "Pink", "Yellow"], more: true },
  { title: "Price", items: ["$300 to $500", "$300 to $500", "$300 to $500", "$300 to $500"] },
];

function ChocolatesPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Announcement */}
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-2 text-muted-foreground uppercase">
        Order Desserts for Local Pickup
      </div>

      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      {/* Nav */}
      <header className="bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-lg">🇺🇸</span>
            <span>English</span>
            <ChevronDown className="h-3 w-3" />
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

      {/* Page title + breadcrumbs */}
      <div className="max-w-7xl mx-auto px-6 pt-10 pb-6 text-center">
        <h1 className="font-display text-4xl md:text-5xl text-primary">Chocolates</h1>
        <nav className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-primary">Chocolates</span>
        </nav>
      </div>

      {/* Category chips */}
      <div className="max-w-7xl mx-auto px-6 pb-8">
        <div className="flex flex-wrap gap-3 justify-center">
          {categories.map((c, i) => (
            <button key={i} className="flex items-center gap-2 rounded-md bg-white border border-border px-3 py-2 text-xs hover:border-primary transition">
              <img src={c.img} alt={c.name} className="h-7 w-7 rounded object-cover" />
              <span>{c.name}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main grid: sidebar + products */}
      <div className="max-w-7xl mx-auto px-6 pb-16 grid grid-cols-1 md:grid-cols-[240px_1fr] gap-8">
        {/* Sidebar */}
        <aside className="border border-border rounded-md p-5 h-fit bg-white">
          <div className="flex items-center justify-between pb-4 border-b border-border">
            <h3 className="font-display text-base text-primary">Category</h3>
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="space-y-6 pt-5">
            {filterGroups.map((g, gi) => (
              <div key={gi}>
                <h4 className="text-sm font-semibold text-foreground mb-3">{g.title}</h4>
                <ul className="space-y-2">
                  {g.items.map((it, i) => (
                    <li key={i} className="flex items-center justify-between text-xs">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <span className="h-3.5 w-3.5 rounded-full border border-muted-foreground/50 inline-block" />
                        <span className="text-foreground">{it}</span>
                      </label>
                      <span className="text-muted-foreground">(31)</span>
                    </li>
                  ))}
                </ul>
                {g.more && <button className="mt-2 text-xs underline text-foreground">Show More</button>}
              </div>
            ))}
          </div>
        </aside>

        {/* Product grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {products.map((img, i) => (
            <div key={i} className="bg-white rounded-md overflow-hidden border border-border">
              <div className="aspect-square overflow-hidden">
                <img src={img} alt="Moose Cream" loading="lazy" width={700} height={700} className="w-full h-full object-cover hover:scale-105 transition duration-500" />
              </div>
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-sm text-primary uppercase tracking-wider">Moose Cream</h3>
                  <span className="text-sm text-primary font-semibold">$6.99</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Worem ipsum dolor sit amet consectetur.</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Zigzag before footer */}
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
              {["VISA","AMEX","PayPal","GPay"].map(p => (
                <span key={p} className="bg-background text-primary rounded px-2 py-1 text-[10px] font-semibold">{p}</span>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
