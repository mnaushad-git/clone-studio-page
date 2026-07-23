import { createFileRoute, notFound } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";
import { slugToOccasion } from "@/lib/products";

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
          { title: `${loaderData.occasion} — Terrific Bites` },
          { name: "description", content: `Sweet treats picked for ${loaderData.occasion.toLowerCase()} moments.` },
          { property: "og:title", content: `${loaderData.occasion} — Terrific Bites` },
          { property: "og:description", content: `Sweet treats picked for ${loaderData.occasion.toLowerCase()} moments.` },
          { property: "og:type", content: "website" },
          { name: "twitter:card", content: "summary_large_image" },
        ]
      : [{ title: "Moments — Terrific Bites" }, { name: "robots", content: "noindex" }],
  }),
});

function MomentsPage() {
  const { occasion } = Route.useLoaderData();
  return (
    <ShopGrid
      title={occasion}
      breadcrumb={[{ label: "Moments" }, { label: occasion }]}
      forcedOccasion={occasion}
      showSearch={false}
    />
  );
}
