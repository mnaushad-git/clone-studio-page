import { createFileRoute, notFound } from "@tanstack/react-router";
import { ShopGrid } from "@/components/ShopGrid";
import { slugToRecipient, type Recipient } from "@/lib/products";
import { useT, type TKey } from "@/lib/i18n";

const RECIPIENT_LABEL_KEYS: Record<Recipient, TKey> = {
  "For Him": "shopRecipientForHim",
  "For Her": "shopRecipientForHer",
  "For Kids": "shopRecipientForKids",
  "For Family": "shopRecipientForFamily",
};

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
  const t = useT();
  const { recipient } = Route.useLoaderData() as { recipient: Recipient };
  const recipientLabel = t(RECIPIENT_LABEL_KEYS[recipient]);
  return (
    <ShopGrid
      title={recipientLabel}
      breadcrumb={[{ label: t("recipientsBreadcrumbLabel") }, { label: recipientLabel }]}
      forcedRecipient={recipient}
      showSearch={false}
    />
  );
}
