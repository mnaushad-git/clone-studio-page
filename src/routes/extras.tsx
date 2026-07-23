import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";

export const Route = createFileRoute("/extras")({
  component: () => (
    <ShopGrid title="Extras" breadcrumb={[{ label: "Extras" }]} initialCategory="extras" lockCategory />
  ),
  head: () => ({
    meta: [
      { title: "Extras — Terrific Bites" },
      { name: "description", content: "Little add-ons — mini cheesecakes, donut pairs, ice cream cones and more." },
      { property: "og:title", content: "Extras — Terrific Bites" },
      { property: "og:description", content: "Little add-ons to complete your order." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
