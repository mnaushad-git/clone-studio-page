import { useState } from "react";
import { Star } from "lucide-react";
import { toast } from "sonner";
import { useStore, selectProductReviews, selectAverageRating, reviews as reviewsApi } from "@/lib/store";

export function ProductReviews({ productId }: { productId: string }) {
  const list = useStore(selectProductReviews(productId));
  const avg = useStore(selectAverageRating(productId));
  const user = useStore((s) => s.user);

  const [rating, setRating] = useState(5);
  const [hover, setHover] = useState(0);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [author, setAuthor] = useState(user?.name ?? "");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!author.trim() || !body.trim()) {
      toast.error("Please add your name and review");
      return;
    }
    reviewsApi.add({ productId, author: author.trim(), rating, title: title.trim() || undefined, body: body.trim() });
    setTitle("");
    setBody("");
    setRating(5);
    toast.success("Thanks for the review!");
  };

  return (
    <section className="max-w-7xl mx-auto px-6 pb-16">
      <div className="border border-border rounded-lg bg-white p-6 md:p-10">
        <div className="flex items-baseline justify-between flex-wrap gap-4">
          <h2 className="font-display text-2xl text-primary">Reviews</h2>
          {list.length > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <div className="flex items-center gap-0.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star key={n} className={`h-4 w-4 ${n <= Math.round(avg) ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground/40"}`} />
                ))}
              </div>
              <span className="font-semibold">{avg.toFixed(1)}</span>
              <span className="text-muted-foreground">({list.length})</span>
            </div>
          )}
        </div>

        {/* Existing reviews */}
        <div className="mt-6 space-y-5">
          {list.length === 0 && (
            <p className="text-sm text-muted-foreground">No reviews yet — be the first to share your thoughts.</p>
          )}
          {list.map((r) => (
            <div key={r.id} className="border-b border-border pb-4 last:border-0">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">{r.author}</span>
                <span>·</span>
                <span>{new Date(r.createdAt).toLocaleDateString()}</span>
              </div>
              <div className="mt-1 flex items-center gap-0.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star key={n} className={`h-3.5 w-3.5 ${n <= r.rating ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground/40"}`} />
                ))}
              </div>
              {r.title && <h4 className="mt-2 font-semibold text-sm">{r.title}</h4>}
              <p className="mt-1 text-sm text-muted-foreground leading-relaxed">{r.body}</p>
            </div>
          ))}
        </div>

        {/* New review */}
        <form onSubmit={submit} className="mt-8 border-t border-border pt-8 grid gap-4">
          <h3 className="font-semibold">Write a review</h3>
          <div className="flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                type="button"
                key={n}
                onMouseEnter={() => setHover(n)}
                onMouseLeave={() => setHover(0)}
                onClick={() => setRating(n)}
                aria-label={`${n} star${n > 1 ? "s" : ""}`}
              >
                <Star className={`h-6 w-6 transition ${n <= (hover || rating) ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground/40"}`} />
              </button>
            ))}
          </div>
          <input
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            placeholder="Your name"
            className="border border-border rounded-md px-3 py-2 text-sm bg-white"
          />
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Review title (optional)"
            className="border border-border rounded-md px-3 py-2 text-sm bg-white"
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Share your experience…"
            rows={4}
            className="border border-border rounded-md px-3 py-2 text-sm bg-white resize-none"
          />
          <button type="submit" className="justify-self-start bg-primary text-primary-foreground rounded-md px-5 py-2 text-sm font-medium hover:opacity-90">
            Submit review
          </button>
        </form>
      </div>
    </section>
  );
}
