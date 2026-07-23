import { createFileRoute } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";

export const Route = createFileRoute("/chocolates")({
  component: () => (
    <ShopGrid title="Chocolates" breadcrumb={[{ label: "Chocolates" }]} initialCategory="chocolates" lockCategory />
  ),
  head: () => ({
    meta: [
      { title: "Chocolates — Terrific Bites" },
      { name: "description", content: "Handmade truffles, pralines and ganache bites." },
      { property: "og:title", content: "Chocolates — Terrific Bites" },
      { property: "og:description", content: "Handmade truffles, pralines and ganache bites." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});
