import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, Play, Truck, Headphones, RotateCcw } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { useT } from "@/lib/i18n";

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
  const t = useT();
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />


      {/* Page banner */}
      <section className="relative bg-primary text-primary-foreground overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 py-16 text-center relative">
          {/* Decorative icons */}
          <span className="absolute left-6 top-6 opacity-30 text-2xl">🎂</span>
          <span className="absolute left-24 bottom-6 opacity-30 text-2xl">🛍️</span>
          <span className="absolute right-6 top-6 opacity-30 text-2xl">🍩</span>
          <span className="absolute right-24 bottom-6 opacity-30 text-2xl">🔔</span>
          <h1 className="font-display text-4xl md:text-5xl">{t("aboutBannerTitle")}</h1>
          <div className="mt-3 flex items-center justify-center gap-2 text-xs opacity-80">
            <Link to="/" className="hover:opacity-100">{t("aboutBreadcrumbHome")}</Link>
            <ChevronRight className="h-3 w-3" />
            <span>{t("aboutBreadcrumbCurrent")}</span>
          </div>
        </div>
      </section>

      {/* Story */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
        <div className="relative">
          <img src={donutsHero} alt={t("aboutDonutsAlt")} loading="lazy" width={900} height={900} className="w-full max-w-md rounded-full aspect-square object-cover" />
          <img src={aboutTestimonial} alt={t("aboutPersonDonutAlt")} loading="lazy" width={600} height={600} className="absolute bottom-4 left-1/3 w-40 h-40 rounded-full object-cover border-4 border-background" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">{t("aboutStoryKicker")}</p>
          <h2 className="mt-2 font-display text-3xl md:text-4xl text-primary uppercase">{t("aboutStoryTitle")}</h2>
          <p className="mt-5 text-sm text-muted-foreground leading-relaxed">{t("aboutStoryPara1")}</p>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{t("aboutStoryPara2")}</p>
          <button className="mt-6 rounded-md bg-primary px-6 py-3 text-sm text-primary-foreground">{t("aboutShopCta")}</button>
        </div>
      </section>

      {/* Testimonial */}
      <section className="bg-secondary">
        <div className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <p className="text-sm italic text-foreground/80 leading-relaxed max-w-lg">
              {t("aboutTestimonialQuote")}
            </p>
            <p className="mt-6 text-sm font-medium">{t("aboutTestimonialAuthor")}</p>
            <div className="mt-8 flex gap-3">
              <button aria-label={t("aboutPrevAriaLabel")} className="h-9 w-9 rounded-full border flex items-center justify-center"><ChevronLeft className="h-4 w-4" /></button>
              <button aria-label={t("aboutNextAriaLabel")} className="h-9 w-9 rounded-full border flex items-center justify-center"><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
          <div className="relative flex justify-center md:justify-end">
            <div className="relative">
              <img src={aboutTestimonial} alt={t("aboutHappyCustomerAlt")} loading="lazy" width={800} height={800} className="w-72 h-72 md:w-80 md:h-80 rounded-full object-cover" style={{ borderTopLeftRadius: "9999px", borderTopRightRadius: "9999px", borderBottomLeftRadius: "60% 40%", borderBottomRightRadius: "40% 60%" }} />
              <span className="absolute -bottom-4 left-4 font-display text-6xl text-primary/60">,,</span>
            </div>
          </div>
        </div>
      </section>

      {/* Vision */}
      <section className="max-w-7xl mx-auto px-6 py-20 grid md:grid-cols-2 gap-12 items-center">
        <div className="relative flex justify-center">
          <div className="absolute -top-4 -left-2 w-24 h-24 rounded-full bg-secondary" />
          <img src={aboutVision} alt={t("aboutBakerAlt")} loading="lazy" width={800} height={800} className="relative w-80 h-80 md:w-96 md:h-96 rounded-full object-cover" />
          <span className="absolute top-4 right-8 text-3xl">🧁</span>
          <span className="absolute bottom-6 left-6 text-2xl">🍰</span>
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-muted-foreground">{t("aboutVisionKicker")}</p>
          <h2 className="mt-2 font-display text-3xl md:text-4xl text-primary uppercase">{t("aboutVisionTitle")}</h2>
          <p className="mt-5 text-sm text-muted-foreground leading-relaxed">{t("aboutStoryPara1")}</p>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{t("aboutStoryPara2")}</p>
          <button className="mt-6 rounded-md bg-primary px-6 py-3 text-sm text-primary-foreground">{t("aboutShopCta")}</button>
        </div>
      </section>

      {/* Video banner */}
      <section className="relative">
        <img src={aboutBanner} alt={t("aboutVideoBannerAlt")} loading="lazy" width={1600} height={700} className="w-full h-[380px] md:h-[460px] object-cover" />
        <div className="absolute inset-0 bg-black/40 flex flex-col items-center justify-center text-center px-6">
          <h2 className="font-display text-3xl md:text-5xl text-white max-w-2xl uppercase">{t("aboutVideoTitle")}</h2>
          <button aria-label={t("aboutPlayAriaLabel")} className="mt-6 h-14 w-14 rounded-full border-2 border-white/80 flex items-center justify-center hover:bg-white/10">
            <Play className="h-5 w-5 text-white fill-white" />
          </button>
        </div>
      </section>

      {/* Feature strip */}
      <section className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-3 gap-8 text-center">
        {[
          { icon: Truck, title: t("aboutFeatureShippingTitle") },
          { icon: Headphones, title: t("aboutFeatureSupportTitle") },
          { icon: RotateCcw, title: t("aboutFeatureReturnTitle") },
        ].map(({ icon: Icon, title }) => (
          <div key={title} className="flex flex-col items-center">
            <div className="h-14 w-14 rounded-full bg-secondary flex items-center justify-center text-primary">
              <Icon className="h-6 w-6" />
            </div>
            <h3 className="mt-4 font-display uppercase text-sm tracking-wider text-primary">{title}</h3>
            <p className="mt-2 text-xs text-muted-foreground max-w-[220px]">{t("aboutFeatureDesc")}</p>
          </div>
        ))}
      </section>

      <SiteFooter />
    </div>
  );
}
