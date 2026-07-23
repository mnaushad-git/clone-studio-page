import { createFileRoute, notFound } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";
import { slugToRecipient } from "@/lib/products";

export const Route = createFileRoute("/recipients/$slug")({
  loader: ({ params }) => {
    const recipient = slugToRecipient(params.slug);
    if (!recipient) throw notFound();
    return { recipient };
  },
  component: RecipientsPage,
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [
          { title: `${loaderData.recipient} — Terrific Bites` },
          { name: "description", content: `Gift ideas ${loaderData.recipient.toLowerCase()}.` },
          { property: "og:title", content: `${loaderData.recipient} — Terrific Bites` },
          { property: "og:description", content: `Gift ideas ${loaderData.recipient.toLowerCase()}.` },
          { property: "og:type", content: "website" },
          { name: "twitter:card", content: "summary_large_image" },
        ]
      : [{ title: "Recipients — Terrific Bites" }, { name: "robots", content: "noindex" }],
  }),
});

function RecipientsPage() {
  const { recipient } = Route.useLoaderData();
  return (
    <ShopGrid
      title={recipient}
      breadcrumb={[{ label: "Recipients" }, { label: recipient }]}
      forcedRecipient={recipient}
      showSearch={false}
    />
  );
}
