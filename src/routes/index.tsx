import { createFileRoute } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, ShoppingBag, User, Facebook, Instagram, Twitter, Youtube } from "lucide-react";

import hero from "@/assets/hero-cupcake.jpg";
import prodSwiss from "@/assets/prod-swiss.jpg";
import prodMoose from "@/assets/prod-moose.jpg";
import prodButter from "@/assets/prod-butter.jpg";
import prodLight from "@/assets/prod-light.jpg";
import giftDonuts from "@/assets/gift-donuts.jpg";
import giftButter from "@/assets/gift-butter.jpg";
import giftCream from "@/assets/gift-cream.jpg";
import giftWhisk from "@/assets/gift-whisk.jpg";
import divine1 from "@/assets/divine-1.jpg";
import divine2 from "@/assets/divine-2.jpg";
import divine3 from "@/assets/divine-3.jpg";
import divine4 from "@/assets/divine-4.jpg";
import catering from "@/assets/catering.jpg";
import donutsHero from "@/assets/donuts-hero.jpg";
import personDonut from "@/assets/person-donut.jpg";

export const Route = createFileRoute("/")({
  component: Index,
  head: () => ({
    meta: [
      { title: "Terrific Bites — Artisan Cupcakes, Donuts & Desserts" },
      { name: "description", content: "Handcrafted cupcakes, donuts and indulgent desserts. Order online for local pickup or event catering." },
      { property: "og:title", content: "Terrific Bites — Artisan Cupcakes & Desserts" },
      { property: "og:description", content: "Handcrafted cupcakes, donuts and indulgent desserts. Order online for local pickup." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const products = [
  { name: "Swiss Frosting", img: prodSwiss },
  { name: "Moose Cream", img: prodMoose },
  { name: "Butter Frosting", img: prodButter },
  { name: "Light Sponge", img: prodLight },
];

const gifts = [
  { name: "Birthday Pair Cups", img: giftDonuts, bg: "oklch(0.85 0.06 300)" },
  { name: "Butter Frosting Delight", img: giftButter, bg: "oklch(0.92 0.15 90)" },
  { name: "Cream & cheese Donut", img: giftCream, bg: "oklch(0.94 0.03 60)" },
  { name: "Whisk & Whimsy Cupcak", img: giftWhisk, bg: "oklch(0.82 0.15 150)" },
];

const divine = [
  { name: "Sprinkle Cupcakes", img: divine1 },
  { name: "Sprinkle Cupcakes", img: divine2 },
  { name: "Sprinkle Cupcakes", img: divine3 },
  { name: "Sprinkle Cupcakes", img: divine4 },
];

function SectionHead({ title, kicker }: { title: string; kicker?: string }) {
  return (
    <div className="flex items-end justify-between gap-6 mb-8">
      <div>
        <h2 className="font-display text-3xl md:text-4xl text-primary">{title}</h2>
        {kicker && <p className="mt-2 text-sm text-muted-foreground max-w-md">{kicker}</p>}
      </div>
      <button className="shrink-0 rounded-md bg-primary px-5 py-2 text-sm text-primary-foreground hover:opacity-90 transition">
        View More
      </button>
    </div>
  );
}

function Index() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Announcement */}
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-2 text-muted-foreground uppercase">
        Order Desserts for Local Pickup
      </div>

      {/* Zigzag divider */}
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      {/* Nav */}
      <header className="bg-white">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm">
            <span className="text-lg">🇺🇸</span>
            <span>English</span>
          </div>
          <a href="#" className="font-script text-3xl text-primary leading-none">Terrific<br /><span className="ml-6">Bites</span></a>
          <div className="flex items-center gap-6 text-sm">
            <button className="flex items-center gap-2"><User className="h-4 w-4" /> My Account</button>
            <button className="flex items-center gap-2"><ShoppingBag className="h-4 w-4" /> Cart</button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative bg-black text-white overflow-hidden">
        <img src={hero} alt="Chocolate cupcake with cream and chocolate splash" width={1600} height={900} className="absolute inset-0 w-full h-full object-cover object-right opacity-95" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/85 via-black/40 to-transparent" />
        <div className="relative max-w-7xl mx-auto px-6 py-24 md:py-32 min-h-[520px]">
          <div className="max-w-lg">
            <h1 className="font-display text-4xl md:text-5xl leading-tight uppercase">
              Not just acai,<br />it's terrific bites
            </h1>
            <p className="mt-5 text-sm text-white/70 max-w-md leading-relaxed">
              Handcrafted with premium ingredients — soft sponge, silky frosting, and flavors that turn ordinary moments into something to remember.
            </p>
            <button className="mt-7 rounded-md bg-primary px-6 py-3 text-sm hover:opacity-90 transition">Choose Now</button>
          </div>
        </div>
        <button aria-label="prev" className="absolute left-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white/10 backdrop-blur flex items-center justify-center hover:bg-white/20"><ChevronLeft className="h-5 w-5" /></button>
        <button aria-label="next" className="absolute right-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white/10 backdrop-blur flex items-center justify-center hover:bg-white/20"><ChevronRight className="h-5 w-5" /></button>
        <div className="absolute bottom-5 left-1/2 -translate-x-1/2 flex gap-2">
          {[0,1,2,3].map(i => (
            <span key={i} className={`h-1.5 rounded-full ${i===2 ? "w-6 bg-primary" : "w-1.5 bg-white/50"}`} />
          ))}
        </div>
      </section>

      {/* Products */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <SectionHead title="Our Products" kicker="Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {products.map((p) => (
            <div key={p.name} className="group">
              <div className="aspect-square overflow-hidden rounded-md bg-secondary">
                <img src={p.img} alt={p.name} loading="lazy" width={700} height={700} className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
              </div>
              <h3 className="mt-3 font-display text-sm text-primary uppercase tracking-wider">{p.name}</h3>
            </div>
          ))}
        </div>
      </section>

      {/* Gifts */}
      <section className="max-w-7xl mx-auto px-6 py-8">
        <SectionHead title="Gifts For Every Moment" kicker="Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {gifts.map((g) => (
            <div key={g.name} className="text-center">
              <div className="aspect-square rounded-full overflow-hidden flex items-center justify-center" style={{ background: g.bg }}>
                <img src={g.img} alt={g.name} loading="lazy" width={700} height={700} className="w-full h-full object-cover" />
              </div>
              <h3 className="mt-4 font-display text-sm text-primary uppercase tracking-wider">{g.name}</h3>
            </div>
          ))}
        </div>
      </section>

      {/* Divine treats */}
      <section className="mt-16 py-16 bg-cream">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-10">
            <h2 className="font-display text-3xl md:text-4xl text-primary">Divine Treats & Indulgent Desserts</h2>
            <p className="mt-2 text-sm text-muted-foreground">Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit.</p>
          </div>
          <div className="relative">
            <button aria-label="prev" className="absolute -left-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white shadow flex items-center justify-center z-10"><ChevronLeft className="h-5 w-5" /></button>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {divine.map((d, i) => (
                <div key={i}>
                  <div className="aspect-square overflow-hidden rounded-md">
                    <img src={d.img} alt={d.name} loading="lazy" width={700} height={700} className="w-full h-full object-cover" />
                  </div>
                  <h3 className="mt-3 font-display text-sm text-primary uppercase tracking-wider">{d.name}</h3>
                  <p className="text-xs text-muted-foreground mt-1">$4.5</p>
                </div>
              ))}
            </div>
            <button aria-label="next" className="absolute -right-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white shadow flex items-center justify-center z-10"><ChevronRight className="h-5 w-5" /></button>
          </div>
        </div>
      </section>

      {/* What's new */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="flex items-end justify-between gap-6 mb-8">
          <div>
            <h2 className="font-display text-3xl md:text-4xl text-primary">What's New</h2>
            <p className="mt-2 text-sm text-muted-foreground max-w-md">Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit.</p>
          </div>
          <div className="flex gap-2">
            <button aria-label="prev" className="h-8 w-8 rounded-full border flex items-center justify-center"><ChevronLeft className="h-4 w-4" /></button>
            <button aria-label="next" className="h-8 w-8 rounded-full border flex items-center justify-center"><ChevronRight className="h-4 w-4" /></button>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {products.map((p) => (
            <div key={"new-" + p.name}>
              <div className="aspect-square overflow-hidden rounded-md bg-secondary">
                <img src={p.img} alt={p.name} loading="lazy" width={700} height={700} className="w-full h-full object-cover" />
              </div>
              <h3 className="mt-3 font-display text-sm text-primary uppercase tracking-wider">{p.name}</h3>
            </div>
          ))}
        </div>
      </section>

      {/* Event Catering */}
      <section className="grid md:grid-cols-2 items-stretch">
        <div className="bg-secondary flex items-center justify-center px-8 py-16 md:py-24">
          <div className="max-w-md text-center">
            <h2 className="font-display text-3xl md:text-4xl text-primary">Event Catering & Customized Gifting</h2>
            <p className="mt-4 text-sm text-muted-foreground">Consectetur. Eros ullamcorper velit pulvinar non maecenas magna eget. Malesuada scelerisque.</p>
            <button className="mt-6 rounded-md bg-primary px-6 py-3 text-sm text-primary-foreground">Lets Shop Now</button>
          </div>
        </div>
        <div className="bg-white flex items-center justify-center">
          <img src={catering} alt="Pink frosted cookies" loading="lazy" width={1000} height={800} className="max-h-[500px] object-contain" />
        </div>
      </section>

      {/* Cupcake Perfection */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-10 items-center">
        <div className="relative">
          <img src={donutsHero} alt="Donuts" loading="lazy" width={900} height={900} className="w-full rounded-full aspect-square object-cover max-w-md" />
          <img src={personDonut} alt="Person with donuts" loading="lazy" width={600} height={600} className="absolute bottom-4 left-1/3 w-40 h-40 rounded-full object-cover border-4 border-background" />
        </div>
        <div>
          <h2 className="font-display text-3xl md:text-4xl text-primary uppercase">Cupcake Perfection: Love-Baked by Terrific Bites</h2>
          <p className="mt-5 text-sm text-muted-foreground">Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit pulvinar non maecenas magna eget. Malesuada scelerisque vitae augue.</p>
          <p className="mt-3 text-sm text-muted-foreground">Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit pulvinar non maecenas magna eget.</p>
          <button className="mt-6 rounded-md bg-primary px-6 py-3 text-sm text-primary-foreground">Lets Shop</button>
        </div>
      </section>

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
