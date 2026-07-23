import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";

export const Route = createFileRoute("/donuts")({
  component: () => (
    <ShopGrid title="Donuts" breadcrumb={[{ label: "Donuts" }]} initialCategory="donuts" lockCategory />
  ),
  head: () => ({
    meta: [
      { title: "Donuts — Terrific Bites" },
      { name: "description", content: "Fluffy filled and glazed donuts baked daily." },
      { property: "og:title", content: "Donuts — Terrific Bites" },
      { property: "og:description", content: "Fluffy filled and glazed donuts baked daily." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
