import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";

export const Route = createFileRoute("/gifts")({
  component: () => (
    <ShopGrid title="Gifts" breadcrumb={[{ label: "Gifts" }]} initialCategory="gifts" lockCategory />
  ),
  head: () => ({
    meta: [
      { title: "Gifts — Terrific Bites" },
      { name: "description", content: "Curated dessert gift boxes for every occasion." },
      { property: "og:title", content: "Gifts — Terrific Bites" },
      { property: "og:description", content: "Curated dessert gift boxes for every occasion." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
