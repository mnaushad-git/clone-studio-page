import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ChevronRight, Minus, Plus, Cake, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { getProduct, products } from "@/lib/products";
import { cart } from "@/lib/store";

export const Route = createFileRoute("/product/$id")({
  component: ProductPage,
  loader: ({ params }) => {
    const p = getProduct(params.id);
    if (!p) throw notFound();
    return { product: p };
  },
  head: ({ loaderData }) => ({
    meta: loaderData
      ? [
          { title: `${loaderData.product.name} — Terrific Bites` },
          { name: "description", content: loaderData.product.description ?? "Handcrafted dessert from Terrific Bites." },
          { property: "og:title", content: `${loaderData.product.name} — Terrific Bites` },
          { property: "og:description", content: loaderData.product.description ?? "Handcrafted dessert from Terrific Bites." },
          { property: "og:type", content: "product" },
          { name: "twitter:card", content: "summary_large_image" },
        ]
      : [{ title: "Product — Terrific Bites" }, { name: "robots", content: "noindex" }],
  }),
});

const tabs = ["Description", "Storage Instructions", "Ingredients", "Allergens"];

function ProductPage() {
  const { product } = Route.useLoaderData();
  const navigate = useNavigate();
  const thumbs = product.thumbs ?? [product.image];
  const [active, setActive] = useState(0);
  const [sizeIdx, setSizeIdx] = useState(0);
  const [flavorIdx, setFlavorIdx] = useState(0);
  const [qty, setQty] = useState(1);
  const [tab, setTab] = useState(0);
  const [inscription, setInscription] = useState("");

  const selectedSize = product.sizes?.[sizeIdx];
  const selectedFlavor = product.flavors?.[flavorIdx];
  const unitPrice = product.price + (selectedSize?.delta ?? 0);

  const addToCart = () => {
    cart.add({
      productId: product.id,
      qty,
      size: selectedSize?.label,
      flavor: selectedFlavor,
      inscription: inscription || undefined,
      unitPrice,
    });
    toast.success(`${product.name} added to cart`);
  };

  const buyNow = () => {
    addToCart();
    setTimeout(() => navigate({ to: "/customize" }), 200);
  };

  const related = products.filter((p) => p.category === product.category && p.id !== product.id).slice(0, 4);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <SiteHeader />

      <div className="max-w-7xl mx-auto px-6 pt-8">
        <nav className="flex items-center gap-2 text-xs text-muted-foreground">
          <Link to="/" className="hover:text-primary">Home</Link>
          <ChevronRight className="h-3 w-3" />
          <Link to="/chocolates" className="hover:text-primary capitalize">{product.category}</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="text-primary">{product.name}</span>
        </nav>
      </div>

      <section className="max-w-7xl mx-auto px-6 pt-6 pb-16 grid md:grid-cols-2 gap-12">
        <div>
          <div className="bg-secondary rounded-md overflow-hidden aspect-square flex items-center justify-center">
            <img src={thumbs[active]} alt={product.name} className="w-full h-full object-cover" />
          </div>
          {thumbs.length > 1 && (
            <div className="mt-4 grid grid-cols-4 gap-3">
              {thumbs.map((t: string, i: number) => (
                <button key={i} onClick={() => setActive(i)} className={`aspect-square rounded-md overflow-hidden border ${active === i ? "border-primary" : "border-border"}`}>
                  <img src={t} alt="thumbnail" loading="lazy" className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-3xl font-bold text-foreground">${unitPrice.toFixed(2)}</div>
              <div className="text-xs text-muted-foreground mt-1">All prices include VAT</div>
            </div>
            <div className="text-right">
              <div className="flex items-center gap-2 justify-end text-sm">
                <Cake className="h-4 w-4 text-primary" />
                <span className="font-semibold">Earn {Math.round(unitPrice * 4)}</span>
              </div>
              <span className="text-xs underline text-muted-foreground">Terrific points</span>
            </div>
          </div>

          <h1 className="mt-6 font-display text-3xl text-primary">{product.name}</h1>
          {product.description && <p className="mt-2 text-sm text-muted-foreground">{product.description}</p>}

          {product.sizes && (
            <div className="mt-6 grid grid-cols-2 gap-3">
              {product.sizes.map((s, i) => (
                <button key={i} onClick={() => setSizeIdx(i)} className={`flex items-center gap-3 border rounded-md p-3 text-left ${sizeIdx === i ? "border-primary" : "border-border"}`}>
                  <span className={`h-4 w-4 rounded-full border ${sizeIdx === i ? "border-primary" : "border-muted-foreground/50"} flex items-center justify-center`}>
                    {sizeIdx === i && <span className="h-2 w-2 rounded-full bg-primary" />}
                  </span>
                  <span>
                    <span className="block text-sm font-semibold">{s.label}</span>
                    {s.sub && <span className="block text-[11px] text-muted-foreground uppercase tracking-wider">{s.sub}</span>}
                  </span>
                </button>
              ))}
            </div>
          )}

          {product.flavors && (
            <div className="mt-3 grid grid-cols-2 gap-3">
              {product.flavors.map((f, i) => (
                <button key={f} onClick={() => setFlavorIdx(i)} className={`flex items-center gap-3 border rounded-md p-3 uppercase text-sm ${flavorIdx === i ? "border-primary" : "border-border"}`}>
                  <span className={`h-4 w-4 rounded-full border ${flavorIdx === i ? "border-primary" : "border-muted-foreground/50"} flex items-center justify-center`}>
                    {flavorIdx === i && <span className="h-2 w-2 rounded-full bg-primary" />}
                  </span>
                  {f}
                </button>
              ))}
            </div>
          )}

          <div className="mt-6 grid grid-cols-[auto_1fr] gap-3">
            <div className="flex items-center border border-border rounded-md">
              <button onClick={() => setQty(Math.max(1, qty - 1))} className="p-3"><Minus className="h-4 w-4" /></button>
              <span className="w-10 text-center">{qty}</span>
              <button onClick={() => setQty(qty + 1)} className="p-3"><Plus className="h-4 w-4" /></button>
            </div>
            <button onClick={addToCart} className="bg-foreground text-background rounded-md font-semibold hover:opacity-90">Add To Cart</button>
          </div>
          <button onClick={buyNow} className="mt-3 w-full bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:opacity-90">Buy Now</button>

          {product.category === "cakes" && (
            <div className="mt-6">
              <div className="flex items-center justify-between border-b border-border pb-2 text-sm text-muted-foreground">
                <input value={inscription} onChange={(e) => setInscription(e.target.value.slice(0, 22))} placeholder="Add Custom Inscription" className="bg-transparent outline-none flex-1" />
                <span>{inscription.length}/22</span>
              </div>
              <div className="flex items-center justify-between border-b border-border pb-2 text-sm mt-4">
                <span>Select Inscription Color: <span className="text-foreground">White</span></span>
                <ChevronDown className="h-4 w-4" />
              </div>
            </div>
          )}

          <div className="mt-6 border border-border rounded-md p-4">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold">Ways to pay</h4>
              <div className="flex items-center gap-2">
                {["VISA", "PayPal", "APay", "MC"].map(p => (
                  <span key={p} className="bg-secondary text-foreground rounded px-2 py-1 text-[10px] font-semibold">{p}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-6 pb-16">
        <div className="grid grid-cols-2 md:grid-cols-4 border-b border-border">
          {tabs.map((t, i) => (
            <button key={t} onClick={() => setTab(i)} className={`py-4 text-sm ${tab === i ? "text-foreground border-b-2 border-foreground font-semibold" : "text-muted-foreground"}`}>{t}</button>
          ))}
        </div>
        <div className="pt-8 max-w-4xl">
          <h3 className="font-semibold mb-4">{tabs[tab]}</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">
            {tab === 0 && (product.description ?? "Made fresh in-house with premium ingredients.")}
            {tab === 1 && "Best enjoyed within 48 hours. Store in a cool, dry place away from direct sunlight. Refrigerate items containing cream or dairy."}
            {tab === 2 && "Flour, sugar, butter, eggs, milk, vanilla, natural food coloring, chocolate, and other ingredients specific to this product."}
            {tab === 3 && "Contains: wheat, dairy, eggs. May contain traces of nuts, soy and sesame. Please contact us for full allergen information."}
          </p>
        </div>
      </section>

      {related.length > 0 && (
        <section className="max-w-7xl mx-auto px-6 pb-16">
          <div className="bg-secondary rounded-lg p-8">
            <h2 className="font-display text-2xl text-primary mb-6">You May Also Like</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
              {related.map((r) => (
                <Link key={r.id} to="/product/$id" params={{ id: r.id }} className="group">
                  <div className="aspect-square overflow-hidden rounded-md">
                    <img src={r.image} alt={r.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition duration-500" />
                  </div>
                  <h3 className="mt-3 font-display text-primary text-sm">{r.name}</h3>
                  <div className="text-xs text-muted-foreground">${r.price.toFixed(2)}</div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <SiteFooter />
    </div>
  );
}
