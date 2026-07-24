import { useMemo, useRef, useState } from "react";
import { BadgeCheck, Camera, Star, X } from "lucide-react";
import { toast } from "sonner";
import { useStore, selectAverageRating, selectHasPurchased, reviews as reviewsApi } from "@/lib/store";

export function ProductReviews({ productId }: { productId: string }) {
  const allReviews = useStore((s) => s.reviews);
  const list = useMemo(
    () => allReviews.filter((r) => r.productId === productId).sort((a, b) => b.createdAt - a.createdAt),
    [allReviews, productId],
  );
  const avg = useStore(selectAverageRating(productId));
  const user = useStore((s) => s.user);
  const hasPurchased = useStore(selectHasPurchased(productId));

  const [rating, setRating] = useState(5);
  const [hover, setHover] = useState(0);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [author, setAuthor] = useState(user?.name ?? "");
  const [photos, setPhotos] = useState<string[]>([]);
  const fileInput = useRef<HTMLInputElement>(null);

  const addPhotos = (files: FileList | null) => {
    if (!files) return;
    const remaining = 3 - photos.length;
    const picks = Array.from(files).slice(0, remaining);
    picks.forEach((f) => {
      if (f.size > 800_000) { toast.error(`${f.name} is too large (max 800KB)`); return; }
      const reader = new FileReader();
      reader.onload = () => setPhotos((p) => (p.length < 3 ? [...p, String(reader.result)] : p));
      reader.readAsDataURL(f);
    });
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!author.trim() || !body.trim()) { toast.error("Please add your name and review"); return; }
    reviewsApi.add({
      productId, author: author.trim(), rating,
      title: title.trim() || undefined, body: body.trim(),
      photos: photos.length ? photos : undefined,
      verified: hasPurchased,
    });
    setTitle(""); setBody(""); setRating(5); setPhotos([]);
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

        <div className="mt-6 space-y-5">
          {list.length === 0 && (
            <p className="text-sm text-muted-foreground">No reviews yet — be the first to share your thoughts.</p>
          )}
          {list.map((r) => (
            <div key={r.id} className="border-b border-border pb-4 last:border-0">
              <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                <span className="font-semibold text-foreground">{r.author}</span>
                {r.verified && (
                  <span className="inline-flex items-center gap-1 text-green-700 bg-green-50 px-2 py-0.5 rounded text-[10px] font-semibold">
                    <BadgeCheck className="h-3 w-3" /> Verified purchase
                  </span>
                )}
                <span>·</span>
                <span>{new Date(r.createdAt).toLocaleDateString()}</span>
              </div>
              <div className="mt-1 flex items-center gap-0.5">
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star key={n} className={`h-3 w-3 ${n <= r.rating ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground/40"}`} />
                ))}
              </div>
              {r.title && <p className="mt-2 font-semibold text-sm">{r.title}</p>}
              <p className="mt-1 text-sm text-muted-foreground">{r.body}</p>
              {r.photos && r.photos.length > 0 && (
                <div className="mt-3 flex gap-2 flex-wrap">
                  {r.photos.map((src, i) => (
                    <img key={i} src={src} alt="Review photo" className="h-20 w-20 object-cover rounded border border-border" />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <form onSubmit={submit} className="mt-8 pt-6 border-t border-border">
          <h3 className="font-display text-lg text-primary">Write a review</h3>
          {hasPurchased && (
            <p className="mt-1 text-xs text-green-700 inline-flex items-center gap-1">
              <BadgeCheck className="h-3 w-3" /> Your review will be marked as a verified purchase.
            </p>
          )}
          <div className="mt-3 flex items-center gap-1">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onMouseEnter={() => setHover(n)}
                onMouseLeave={() => setHover(0)}
                onClick={() => setRating(n)}
                aria-label={`Rate ${n} star`}
              >
                <Star className={`h-6 w-6 transition ${n <= (hover || rating) ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground/40"}`} />
              </button>
            ))}
          </div>
          <div className="mt-3 grid sm:grid-cols-2 gap-3">
            <input value={author} onChange={(e) => setAuthor(e.target.value)} placeholder="Your name" className="border border-border rounded-md px-3 py-2 text-sm" />
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title (optional)" className="border border-border rounded-md px-3 py-2 text-sm" />
          </div>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={4} placeholder="Tell us what you thought…" className="mt-3 w-full border border-border rounded-md px-3 py-2 text-sm" />

          <div className="mt-3">
            <div className="flex items-center gap-2 flex-wrap">
              <button
                type="button"
                onClick={() => fileInput.current?.click()}
                disabled={photos.length >= 3}
                className="inline-flex items-center gap-1 text-xs border border-border rounded-md px-3 py-2 hover:bg-muted disabled:opacity-50"
              >
                <Camera className="h-3 w-3" /> Add photos ({photos.length}/3)
              </button>
              <input
                ref={fileInput}
                type="file"
                multiple
                accept="image/*"
                className="hidden"
                onChange={(e) => { addPhotos(e.target.files); e.target.value = ""; }}
              />
              {photos.map((src, i) => (
                <div key={i} className="relative">
                  <img src={src} alt="preview" className="h-14 w-14 object-cover rounded border border-border" />
                  <button
                    type="button"
                    onClick={() => setPhotos((p) => p.filter((_, idx) => idx !== i))}
                    className="absolute -top-1 -end-1 h-4 w-4 rounded-full bg-black/60 text-white flex items-center justify-center"
                  >
                    <X className="h-2.5 w-2.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <button type="submit" className="mt-4 bg-primary text-primary-foreground rounded-md px-5 py-2 text-sm font-semibold hover:bg-primary/90">
            Post review
          </button>
        </form>
      </div>
    </section>
  );
}
