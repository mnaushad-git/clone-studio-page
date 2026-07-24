import { createFileRoute, notFound, Link } from "@tanstack/react-router";
import { SiteHeader } from "@/components/SiteHeader";
import { ShopGrid } from "@/components/ShopGrid";
import { slugToOccasion, products } from "@/lib/products";

const OCCASION_HERO: Record<string, { subtitle: string; blurb: string; accent: string }> = {
  Birthday: { subtitle: "Make the day unforgettable", blurb: "Show-stopping cakes, candle-ready cupcakes, and treat boxes built for singing 'happy birthday' at least twice.", accent: "🎂" },
  Anniversary: { subtitle: "Sweeter with every year", blurb: "Refined desserts and elegant hampers to mark the milestones that matter.", accent: "💐" },
  Wedding: { subtitle: "Say 'I do' to something delicious", blurb: "From bespoke tiered cakes to sharing platters, curated for the biggest day.", accent: "💍" },
  Graduation: { subtitle: "Sugar-dust the achievement", blurb: "Celebration bites and gift sets for every capped-and-gowned occasion.", accent: "🎓" },
  Congratulations: { subtitle: "Big news deserves a big treat", blurb: "New job, new baby, new home — mark the moment sweetly.", accent: "🎉" },
  "Thank You": { subtitle: "Gratitude, gift-wrapped", blurb: "Elegant, share-worthy boxes that say more than a card ever could.", accent: "💌" },
};

export const Route = createFileRoute("/moments/$slug")({
  loader: ({ params }) => {
    const occasion = slugToOccasion(params.slug);
    if (!occasion) throw notFound();
    return { occasion };
  },
  component: MomentsPage,
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [
          { title: `${loaderData.occasion} gifts & cakes — Terrific Bites` },
          { name: "description", content: `Sweet treats picked for ${loaderData.occasion.toLowerCase()} moments — delivered same-day across the region.` },
          { property: "og:title", content: `${loaderData.occasion} gifts — Terrific Bites` },
          { property: "og:description", content: `Curated desserts for ${loaderData.occasion.toLowerCase()}.` },
          { property: "og:type", content: "website" },
          { name: "twitter:card", content: "summary_large_image" },
        ]
      : [{ title: "Moments — Terrific Bites" }, { name: "robots", content: "noindex" }],
  }),
});

function MomentsPage() {
  const { occasion } = Route.useLoaderData();
  const hero = OCCASION_HERO[occasion] ?? { subtitle: "Handpicked for the moment", blurb: "Sweet treats delivered with care.", accent: "✨" };
  const sample = products.find((p) => p.occasions?.includes(occasion)) ?? products[0];

  const HeroBlock = (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0">
        <img src={sample.image} alt="" className="h-full w-full object-cover opacity-25" />
        <div className="absolute inset-0 bg-gradient-to-b from-background via-background/80 to-background" />
      </div>
      <div className="relative max-w-4xl mx-auto px-6 py-14 sm:py-20 text-center">
        <div className="text-4xl">{hero.accent}</div>
        <p className="mt-3 text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
          <Link to="/moments" className="hover:text-primary">Moments</Link> · {occasion}
        </p>
        <h1 className="font-display text-4xl sm:text-5xl text-primary mt-2">{occasion}</h1>
        <p className="mt-3 font-display text-lg text-primary/70 italic">{hero.subtitle}</p>
        <p className="mt-4 text-sm text-muted-foreground max-w-2xl mx-auto">{hero.blurb}</p>
      </div>
    </section>
  );

  return (
    <ShopGrid
      title={occasion}
      breadcrumb={[{ label: "Moments" }, { label: occasion }]}
      forcedOccasion={occasion}
      showSearch={false}
      hero={HeroBlock}
    />
  );
}
