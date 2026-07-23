import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { OCCASIONS, occasionToSlug, products } from "@/lib/products";

export const Route = createFileRoute("/moments/")({
  component: MomentsIndex,
  head: () => ({
    meta: [
      { title: "Moments — Terrific Bites" },
      { name: "description", content: "Shop by the moment — birthdays, anniversaries, weddings and more." },
      { property: "og:title", content: "Moments — Terrific Bites" },
      { property: "og:description", content: "Shop by the moment — desserts for every celebration." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

function MomentsIndex() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

      <div className="max-w-7xl mx-auto px-6 pt-10 pb-6 text-center">
        <h1 className="font-display text-4xl md:text-5xl text-primary">Moments</h1>
        <nav className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-primary">Moments</span>
        </nav>
        <p className="mt-4 text-sm text-muted-foreground max-w-xl mx-auto">
          Handpicked treats for every celebration — pick the moment, we'll do the rest.
        </p>
      </div>

      <div className="max-w-7xl mx-auto px-6 pb-16 grid grid-cols-2 md:grid-cols-3 gap-5">
        {OCCASIONS.map((o) => {
          const sample = products.find((p) => p.occasions?.includes(o)) ?? products[0];
          return (
            <Link
              key={o}
              to="/moments/$slug"
              params={{ slug: occasionToSlug(o) }}
              className="relative aspect-[4/3] rounded-lg overflow-hidden group"
            >
              <img src={sample.image} alt={o} className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition duration-500" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
              <span className="absolute inset-x-0 bottom-5 text-center text-white font-display text-2xl tracking-wide">
                {o}
              </span>
            </Link>
          );
        })}
      </div>

      <SiteFooter />
    </div>
  );
}
