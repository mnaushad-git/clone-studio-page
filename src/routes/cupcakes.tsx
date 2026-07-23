import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";

export const Route = createFileRoute("/cupcakes")({
  component: () => (
    <ShopGrid title="Cupcakes" breadcrumb={[{ label: "Cupcakes" }]} initialCategory="cupcakes" lockCategory />
  ),
  head: () => ({
    meta: [
      { title: "Cupcakes — Terrific Bites" },
      { name: "description", content: "Handcrafted cupcakes in Swiss, butter and mousse frostings." },
      { property: "og:title", content: "Cupcakes — Terrific Bites" },
      { property: "og:description", content: "Silky frostings on sponge baked fresh every day." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
