import { createFileRoute } from "@tanstack/react-router";
import { useStore, reviews as reviewsApi } from "@/lib/store";
import { getProduct } from "@/lib/products";
import { Card, Button, Badge, EmptyState } from "@/components/admin/ui";
import { Star, Trash2 } from "lucide-react";

export const Route = createFileRoute("/admin/reviews")({ component: ReviewsPage });

function ReviewsPage() {
  const list = useStore((s) => s.reviews);

  return (
    <Card title={`Reviews (${list.length})`}>
      {list.length === 0 ? (
        <EmptyState title="No reviews yet" />
      ) : (
        <div className="space-y-3">
          {list.map((r) => {
            const p = getProduct(r.productId);
            return (
              <div key={r.id} className="border rounded-lg p-4 flex gap-4">
                {p && <img src={p.image} alt="" className="h-14 w-14 rounded object-cover" />}
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="font-medium">{p?.name ?? r.productId}</div>
                    <div className="flex text-amber-500">
                      {Array.from({ length: 5 }).map((_, i) => <Star key={i} className={`h-3.5 w-3.5 ${i < r.rating ? "fill-current" : ""}`} />)}
                    </div>
                    {r.verified && <Badge tone="success">Verified</Badge>}
                  </div>
                  {r.title && <div className="text-sm font-medium mt-1">{r.title}</div>}
                  <div className="text-sm text-stone-600 mt-1">{r.body}</div>
                  <div className="text-xs text-stone-400 mt-2">{r.author} · {new Date(r.createdAt).toLocaleDateString()}</div>
                </div>
                <Button variant="ghost" onClick={() => { if (confirm("Delete this review?")) reviewsApi.remove(r.id); }}><Trash2 className="h-4 w-4 text-red-500" /></Button>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
