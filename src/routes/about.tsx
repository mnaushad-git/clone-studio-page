import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, ShoppingBag, User, Facebook, Instagram, Twitter, Youtube, Play, Truck, Headphones, RotateCcw } from "lucide-react";

import donutsHero from "@/assets/donuts-hero.jpg";
import personDonut from "@/assets/person-donut.jpg";
import aboutTestimonial from "@/assets/about-testimonial.jpg";
import aboutVision from "@/assets/about-vision.jpg";
import aboutBanner from "@/assets/about-banner.jpg";

export const Route = createFileRoute("/about")({
  component: About,
  head: () => ({
    meta: [
      { title: "About Us — Terrific Bites" },
      { name: "description", content: "The story, vision and love behind Terrific Bites — handcrafted cupcakes, donuts and desserts baked with care." },
      { property: "og:title", content: "About Us — Terrific Bites" },
      { property: "og:description", content: "The story, vision and love behind Terrific Bites." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

function About() {
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
          </div>
          <Link to="/" className="font-script text-3xl text-primary leading-none">Terrific<br /><span className="ml-6">Bites</span></Link>
          <div className="flex items-center gap-6 text-sm">
            <Link to="/account" className="flex items-center gap-2"><User className="h-4 w-4" /> My Account</Link>
            <button className="flex items-center gap-2"><ShoppingBag className="h-4 w-4" /> Cart</button>
          </div>
        </div>
      </header>

      {/* Page banner */}
      <section className="relative bg-primary text-primary-foreground overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 py-16 text-center relative">
          {/* Decorative icons */}
          <span className="absolute left-6 top-6 opacity-30 text-2xl">🎂</span>
          <span className="absolute left-24 bottom-6 opacity-30 text-2xl">🛍️</span>
          <span className="absolute right-6 top-6 opacity-30 text-2xl">🍩</span>
          <span className="absolute right-24 bottom-6 opacity-30 text-2xl">🔔</span>
          <h1 className="font-display text-4xl md:text-5xl">About us</h1>
          <div className="mt-3 flex items-center justify-center gap-2 text-xs opacity-80">
            <Link to="/" className="hover:opacity-100">Home</Link>
            <ChevronRight className="h-3 w-3" />
            <span>About Us</span>
          </div>
        </div>
      </section>

      {/* Story */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
        <div className="relative">
          <img src={donutsHero} alt="Donuts on pink" loading="lazy" width={900} height={900} className="w-full max-w-md rounded-full aspect-square object-cover" />
          <img src={aboutTestimonial} alt="Person with donut" loading="lazy" width={600} height={600} className="absolute bottom-4 left-1/3 w-40 h-40 rounded-full object-cover border-4 border-background" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Story</p>
          <h2 className="mt-2 font-display text-3xl md:text-4xl text-primary uppercase">Cupcake Perfection: Love-Baked by Terrific Bites</h2>
          <p className="mt-5 text-sm text-muted-foreground leading-relaxed">Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit pulvinar non maecenas magna eget. Malesuada scelerisque vitae augue Malesuada scelerisque vitae.</p>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit pulvinar non maecenas magna eget. Malesuada scelerisque vitae.</p>
          <button className="mt-6 rounded-md bg-primary px-6 py-3 text-sm text-primary-foreground">Lets Shop</button>
        </div>
      </section>

      {/* Testimonial */}
      <section className="bg-secondary">
        <div className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <p className="text-sm italic text-foreground/80 leading-relaxed max-w-lg">
              "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Mauris in dignissim elit. Fusce dictum tristique accumsan. Nulla in rhoncus sapien, eu rutrum diam. Proin nibh tortor, congue nec tellus vitae, ullamcorper pulvinar odio."
            </p>
            <p className="mt-6 text-sm font-medium">Ferdinand Stindl</p>
            <div className="mt-8 flex gap-3">
              <button aria-label="prev" className="h-9 w-9 rounded-full border flex items-center justify-center"><ChevronLeft className="h-4 w-4" /></button>
              <button aria-label="next" className="h-9 w-9 rounded-full border flex items-center justify-center"><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
          <div className="relative flex justify-center md:justify-end">
            <div className="relative">
              <img src={aboutTestimonial} alt="Happy customer" loading="lazy" width={800} height={800} className="w-72 h-72 md:w-80 md:h-80 rounded-full object-cover" style={{ borderTopLeftRadius: "9999px", borderTopRightRadius: "9999px", borderBottomLeftRadius: "60% 40%", borderBottomRightRadius: "40% 60%" }} />
              <span className="absolute -bottom-4 left-4 font-display text-6xl text-primary/60">,,</span>
            </div>
          </div>
        </div>
      </section>

      {/* Vision */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
        <div className="relative flex justify-center">
          <div className="absolute -top-4 -left-2 w-24 h-24 rounded-full bg-secondary" />
          <img src={aboutVision} alt="Baker with cupcakes" loading="lazy" width={800} height={800} className="relative w-80 h-80 md:w-96 md:h-96 rounded-full object-cover" />
          <span className="absolute top-4 right-8 text-3xl">🧁</span>
          <span className="absolute bottom-6 left-6 text-2xl">🍰</span>
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">Our Vision</p>
          <h2 className="mt-2 font-display text-3xl md:text-4xl text-primary uppercase">We Really Love What We Do For Customers</h2>
          <p className="mt-5 text-sm text-muted-foreground leading-relaxed">Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit pulvinar non maecenas magna eget. Malesuada scelerisque vitae augue Malesuada scelerisque vitae.</p>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">Worem ipsum dolor sit amet consectetur. Eros ullamcorper velit pulvinar non maecenas magna eget. Malesuada scelerisque vitae.</p>
          <button className="mt-6 rounded-md bg-primary px-6 py-3 text-sm text-primary-foreground">Lets Shop</button>
        </div>
      </section>

      {/* Video banner */}
      <section className="relative">
        <img src={aboutBanner} alt="Donuts" loading="lazy" width={1600} height={700} className="w-full h-[380px] md:h-[460px] object-cover" />
        <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center text-center px-6">
          <h2 className="font-display text-3xl md:text-5xl text-white max-w-2xl uppercase">We Are Terrific Bites, Who Baked With Love</h2>
          <button aria-label="play" className="mt-6 h-14 w-14 rounded-full border-2 border-white/80 flex items-center justify-center hover:bg-white/10">
            <Play className="h-5 w-5 text-white fill-white" />
          </button>
        </div>
      </section>

      {/* Feature strip */}
      <section className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-8 text-center">
        {[
          { icon: Truck, title: "Free Shipping" },
          { icon: Headphones, title: "24/7 Support" },
          { icon: RotateCcw, title: "1 Days Return Policy" },
        ].map(({ icon: Icon, title }) => (
          <div key={title} className="flex flex-col items-center">
            <div className="h-14 w-14 rounded-full bg-secondary flex items-center justify-center text-primary">
              <Icon className="h-6 w-6" />
            </div>
            <h3 className="mt-4 font-display uppercase text-sm tracking-wider text-primary">{title}</h3>
            <p className="mt-2 text-xs text-muted-foreground max-w-[220px]">Welcome to Sweet Delights, where all your sugary dreams come true!</p>
          </div>
        ))}
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
