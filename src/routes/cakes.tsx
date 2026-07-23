import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";

export const Route = createFileRoute("/cakes")({
  component: () => (
    <ShopGrid title="Cakes" breadcrumb={[{ label: "Cakes" }]} initialCategory="cakes" lockCategory />
  ),
  head: () => ({
    meta: [
      { title: "Cakes — Terrific Bites" },
      { name: "description", content: "Layered celebration cakes, buttercream classics and made-to-order designs." },
      { property: "og:title", content: "Cakes — Terrific Bites" },
      { property: "og:description", content: "Layered celebration cakes handcrafted for every occasion." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
