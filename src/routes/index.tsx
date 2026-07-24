import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { featured } from "@/lib/products";
import hero from "@/assets/hero-cupcake.jpg";
import catering from "@/assets/catering.jpg";
import donutsHero from "@/assets/donuts-hero.jpg";
import personDonut from "@/assets/person-donut.jpg";

export const Route = createFileRoute("/")({
  component: Index,
  head: () => ({
    meta: [
      { title: "Terrific Bites — Artisan Cupcakes, Donuts & Desserts" },
      { name: "description", content: "Handcrafted cupcakes, donuts and indulgent desserts. Order online for local pickup or event catering." },
      { property: "og:title", content: "Terrific Bites — Artisan Cupcakes, Donuts & Desserts" },
      { property: "og:description", content: "Handcrafted cupcakes, donuts and indulgent desserts. Order online for local pickup or event catering." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const gifts = [
  { bg: "oklch(0.85 0.06 300)" },
  { bg: "oklch(0.92 0.15 90)" },
  { bg: "oklch(0.94 0.03 60)" },
  { bg: "oklch(0.82 0.15 150)" },
];

function SectionHead({ title, kicker, to }: { title: string; kicker?: string; to?: string }) {
  return (
    <div className="flex items-end justify-between gap-6 mb-8">
      <div>
        <h2 className="font-display text-3xl md:text-4xl text-primary">{title}</h2>
        {kicker && <p className="mt-2 text-sm text-muted-foreground max-w-md">{kicker}</p>}
      </div>
      <Link to={to ?? "/chocolates"} className="shrink-0 rounded-md bg-primary px-5 py-2 text-sm text-primary-foreground hover:opacity-90 transition">
        View More
      </Link>
    </div>
  );
}

function Index() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

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
            <Link to="/chocolates" className="mt-7 inline-block rounded-md bg-primary px-6 py-3 text-sm hover:opacity-90 transition">Choose Now</Link>
          </div>
        </div>
        <button aria-label="prev" className="absolute left-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white/10 backdrop-blur flex items-center justify-center hover:bg-white/20"><ChevronLeft className="h-5 w-5" /></button>
        <button aria-label="next" className="absolute right-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white/10 backdrop-blur flex items-center justify-center hover:bg-white/20"><ChevronRight className="h-5 w-5" /></button>
      </section>

      {/* Products */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <SectionHead title="Our Products" kicker="Freshly baked cupcakes made with the finest ingredients — pick your favorite flavor." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {featured.hero.map((p) => (
            <Link key={p.id} to="/product/$id" params={{ id: p.id }} className="group">
              <div className="aspect-square overflow-hidden rounded-md bg-secondary">
                <img src={p.image} alt={p.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
              </div>
              <h3 className="mt-3 font-display text-sm text-primary uppercase tracking-wider">{p.name}</h3>
              <p className="text-xs text-muted-foreground mt-1">SAR {p.price.toFixed(2)}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Gifts */}
      <section className="max-w-7xl mx-auto px-6 py-8">
        <SectionHead title="Gifts For Every Moment" kicker="Curated gift boxes for every celebration." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {featured.gifts.map((g, i) => (
            <Link to="/product/$id" params={{ id: g.id }} key={g.id} className="text-center group">
              <div className="aspect-square rounded-full overflow-hidden flex items-center justify-center" style={{ background: gifts[i]?.bg }}>
                <img src={g.image} alt={g.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
              </div>
              <h3 className="mt-4 font-display text-sm text-primary uppercase tracking-wider">{g.name}</h3>
              <p className="text-xs text-muted-foreground">SAR {g.price.toFixed(2)}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Divine treats */}
      <section className="mt-16 py-16 bg-cream">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-10">
            <h2 className="font-display text-3xl md:text-4xl text-primary">Divine Treats & Indulgent Desserts</h2>
            <p className="mt-2 text-sm text-muted-foreground">Small bites, big smiles.</p>
          </div>
          <div className="relative">
            <button aria-label="prev" className="absolute -left-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white shadow flex items-center justify-center z-10"><ChevronLeft className="h-5 w-5" /></button>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              {featured.divine.map((d) => (
                <Link key={d.id} to="/product/$id" params={{ id: d.id }} className="group">
                  <div className="aspect-square overflow-hidden rounded-md">
                    <img src={d.image} alt={d.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
                  </div>
                  <h3 className="mt-3 font-display text-sm text-primary uppercase tracking-wider">{d.name}</h3>
                  <p className="text-xs text-muted-foreground mt-1">SAR {d.price.toFixed(2)}</p>
                </Link>
              ))}
            </div>
            <button aria-label="next" className="absolute -right-3 top-1/2 -translate-y-1/2 h-9 w-9 rounded-full bg-white shadow flex items-center justify-center z-10"><ChevronRight className="h-5 w-5" /></button>
          </div>
        </div>
      </section>

      {/* What's new */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <SectionHead title="What's New" kicker="Fresh out of the oven — try our latest creations." />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {featured.hero.map((p) => (
            <Link to="/product/$id" params={{ id: p.id }} key={"new-" + p.id} className="group">
              <div className="aspect-square overflow-hidden rounded-md bg-secondary">
                <img src={p.image} alt={p.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
              </div>
              <h3 className="mt-3 font-display text-sm text-primary uppercase tracking-wider">{p.name}</h3>
              <p className="text-xs text-muted-foreground mt-1">SAR {p.price.toFixed(2)}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Event Catering */}
      <section className="grid md:grid-cols-2 items-stretch">
        <div className="bg-secondary flex items-center justify-center px-8 py-16 md:py-24">
          <div className="max-w-md text-center">
            <h2 className="font-display text-3xl md:text-4xl text-primary">Event Catering & Customized Gifting</h2>
            <p className="mt-4 text-sm text-muted-foreground">From intimate gatherings to grand celebrations — we handcraft desserts to fit any occasion.</p>
            <Link to="/chocolates" className="mt-6 inline-block rounded-md bg-primary px-6 py-3 text-sm text-primary-foreground">Lets Shop Now</Link>
          </div>
        </div>
        <div className="bg-white flex items-center justify-center">
          <img src={catering} alt="Pink frosted cookies" loading="lazy" className="max-h-[500px] object-contain" />
        </div>
      </section>

      {/* Cupcake Perfection */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-10 items-center">
        <div className="relative">
          <img src={donutsHero} alt="Donuts" loading="lazy" className="w-full rounded-full aspect-square object-cover max-w-md" />
          <img src={personDonut} alt="Person with donuts" loading="lazy" className="absolute bottom-4 left-1/3 w-40 h-40 rounded-full object-cover border-4 border-background" />
        </div>
        <div>
          <h2 className="font-display text-3xl md:text-4xl text-primary uppercase">Cupcake Perfection: Love-Baked by Terrific Bites</h2>
          <p className="mt-5 text-sm text-muted-foreground">Every batch is baked from scratch each morning using local butter, real vanilla and the freshest fruit.</p>
          <Link to="/about" className="mt-6 inline-block rounded-md bg-primary px-6 py-3 text-sm text-primary-foreground">Our Story</Link>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
