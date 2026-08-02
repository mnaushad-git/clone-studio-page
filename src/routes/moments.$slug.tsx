import { createFileRoute, notFound, Link } from "@tanstack/react-router";
import { SiteHeader } from "@/components/SiteHeader";
import { ShopGrid } from "@/components/ShopGrid";
import { occasionToSlug, slugToOccasion, type Occasion } from "@/lib/products";
import { mapSummaryToProduct, useCatalogueProducts } from "@/lib/catalogue-api";
import { useT, type TKey } from "@/lib/i18n";

const OCCASION_LABEL_KEYS: Record<Occasion, TKey> = {
  Birthday: "shopOccasionBirthday",
  Anniversary: "shopOccasionAnniversary",
  Wedding: "shopOccasionWedding",
  Graduation: "shopOccasionGraduation",
  Congratulations: "shopOccasionCongratulations",
  "Thank You": "shopOccasionThankYou",
};

const OCCASION_HERO: Record<string, { subtitleKey: TKey; blurbKey: TKey; accent: string }> = {
  Birthday: { subtitleKey: "momentsHeroBirthdaySubtitle", blurbKey: "momentsHeroBirthdayBlurb", accent: "🎂" },
  Anniversary: { subtitleKey: "momentsHeroAnniversarySubtitle", blurbKey: "momentsHeroAnniversaryBlurb", accent: "💐" },
  Wedding: { subtitleKey: "momentsHeroWeddingSubtitle", blurbKey: "momentsHeroWeddingBlurb", accent: "💍" },
  Graduation: { subtitleKey: "momentsHeroGraduationSubtitle", blurbKey: "momentsHeroGraduationBlurb", accent: "🎓" },
  Congratulations: { subtitleKey: "momentsHeroCongratulationsSubtitle", blurbKey: "momentsHeroCongratulationsBlurb", accent: "🎉" },
  "Thank You": { subtitleKey: "momentsHeroThankYouSubtitle", blurbKey: "momentsHeroThankYouBlurb", accent: "💌" },
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
  const t = useT();
  const { occasion } = Route.useLoaderData() as { occasion: Occasion };
  const hero = OCCASION_HERO[occasion] ?? { subtitleKey: "momentsHeroDefaultSubtitle" as TKey, blurbKey: "momentsHeroDefaultBlurb" as TKey, accent: "✨" };
  const { data: sample } = useCatalogueProducts({ moment: occasionToSlug(occasion), limit: 1 });
  const sampleImage = sample?.items[0] ? mapSummaryToProduct(sample.items[0]).image : undefined;
  const occasionLabel = t(OCCASION_LABEL_KEYS[occasion]);

  const HeroBlock = (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0">
        {sampleImage && <img src={sampleImage} alt="" className="h-full w-full object-cover opacity-25" />}
        <div className="absolute inset-0 bg-gradient-to-b from-background via-background/80 to-background" />
      </div>
      <div className="relative max-w-4xl mx-auto px-6 py-14 sm:py-20 text-center">
        <div className="text-4xl">{hero.accent}</div>
        <p className="mt-3 text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
          <Link to="/moments" className="hover:text-primary">{t("momentsBreadcrumbLabel")}</Link> · {occasionLabel}
        </p>
        <h1 className="font-display text-4xl sm:text-5xl text-primary mt-2">{occasionLabel}</h1>
        <p className="mt-3 font-display text-lg text-primary/70 italic">{t(hero.subtitleKey)}</p>
        <p className="mt-4 text-sm text-muted-foreground max-w-2xl mx-auto">{t(hero.blurbKey)}</p>
      </div>
    </section>
  );

  return (
    <ShopGrid
      title={occasionLabel}
      breadcrumb={[{ label: t("momentsBreadcrumbLabel") }, { label: occasionLabel }]}
      forcedOccasion={occasion}
      showSearch={false}
      hero={HeroBlock}
    />
  );
}
