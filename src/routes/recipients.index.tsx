import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { RECIPIENTS, recipientToSlug, products } from "@/lib/products";

export const Route = createFileRoute("/recipients/")({
  component: RecipientsIndex,
  head: () => ({
    meta: [
      { title: "Recipients — Terrific Bites" },
      { name: "description", content: "Shop by who it's for — for him, for her, for kids, for family." },
      { property: "og:title", content: "Recipients — Terrific Bites" },
      { property: "og:description", content: "Shop by who it's for." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

function RecipientsIndex() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

      <div className="max-w-7xl mx-auto px-6 pt-10 pb-6 text-center">
        <h1 className="font-display text-4xl md:text-5xl text-primary">Recipients</h1>
        <nav className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-primary">Recipients</span>
        </nav>
        <p className="mt-4 text-sm text-muted-foreground max-w-xl mx-auto">
          Curated gifts for the people you love — chosen with care.
        </p>
      </div>

      <div className="max-w-7xl mx-auto px-6 pb-16 grid grid-cols-2 md:grid-cols-4 gap-5">
        {RECIPIENTS.map((r) => {
          const sample = products.find((p) => p.recipients?.includes(r)) ?? products[0];
          return (
            <Link
              key={r}
              to="/recipients/$slug"
              params={{ slug: recipientToSlug(r) }}
              className="relative aspect-[4/5] rounded-lg overflow-hidden group"
            >
              <img src={sample.image} alt={r} className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition duration-500" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
              <span className="absolute inset-x-0 bottom-5 text-center text-white font-display text-xl tracking-wide">
                {r}
              </span>
            </Link>
          );
        })}
      </div>

      <SiteFooter />
    </div>
  );
}
