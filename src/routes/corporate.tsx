import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Building2, Gift, Sparkles, Truck, Check } from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";

export const Route = createFileRoute("/corporate")({
  component: CorporatePage,
  head: () => ({
    meta: [
      { title: "Corporate & Bulk Gifting — Terrific Bites" },
      { name: "description", content: "Impress clients and delight teams with bespoke bulk gifting. Volume pricing, branded packaging, and coordinated delivery." },
      { property: "og:title", content: "Corporate & Bulk Gifting — Terrific Bites" },
      { property: "og:description", content: "Volume pricing, branded packaging, and coordinated delivery across the region." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
});

const TIERS = [
  { qty: "25 – 49", discount: "10% off", perks: ["Branded ribbon", "Grouped delivery"] },
  { qty: "50 – 99", discount: "15% off", perks: ["Custom card printing", "Priority slot", "Dedicated coordinator"] },
  { qty: "100 – 199", discount: "20% off", perks: ["Bespoke packaging", "Multi-city dispatch", "Named account manager"] },
  { qty: "200+", discount: "Custom quote", perks: ["Fully bespoke concept", "Photography of delivery", "Annual contract available"] },
];

function CorporatePage() {
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({
    company: "", contact: "", email: "", phone: "", qty: "50 – 99",
    occasion: "Client appreciation", budget: "", when: "", notes: "",
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.company || !form.contact || !form.email) { toast.error("Please fill required fields"); return; }
    setSubmitted(true);
    toast.success("Request received — our team will be in touch within one business day.");
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <section className="bg-gradient-to-b from-primary/5 to-transparent">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16 text-center">
          <span className="inline-flex items-center gap-1 text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
            <Building2 className="h-3 w-3" /> For Business
          </span>
          <h1 className="font-display text-4xl sm:text-5xl text-primary mt-4">Corporate & Bulk Gifting</h1>
          <p className="mt-3 text-sm sm:text-base text-muted-foreground max-w-2xl mx-auto">
            Say thank you at scale. From client appreciation to onboarding hampers, we handle the sweetness — you handle the wow.
          </p>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-10 grid md:grid-cols-3 gap-6">
        {[
          { icon: Gift, title: "Branded packaging", body: "Custom ribbons, logo-printed cards, foil-stamped boxes." },
          { icon: Truck, title: "Coordinated delivery", body: "Single-slot bulk drop or multi-address dispatch across cities." },
          { icon: Sparkles, title: "Bespoke menus", body: "Design a menu around your brand's flavor, colors, and dietary needs." },
        ].map((f) => (
          <div key={f.title} className="bg-white border border-border rounded-lg p-6">
            <f.icon className="h-6 w-6 text-primary" />
            <h3 className="font-display text-lg text-primary mt-3">{f.title}</h3>
            <p className="mt-2 text-sm text-muted-foreground">{f.body}</p>
          </div>
        ))}
      </section>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 pb-10">
        <h2 className="font-display text-2xl text-primary text-center">Volume pricing</h2>
        <div className="mt-6 overflow-x-auto">
          <table className="w-full min-w-[600px] text-sm bg-white border border-border rounded-lg overflow-hidden">
            <thead className="bg-muted/50 text-primary">
              <tr>
                <th className="text-left px-5 py-3 font-semibold">Quantity</th>
                <th className="text-left px-5 py-3 font-semibold">Discount</th>
                <th className="text-left px-5 py-3 font-semibold">Included perks</th>
              </tr>
            </thead>
            <tbody>
              {TIERS.map((t) => (
                <tr key={t.qty} className="border-t border-border">
                  <td className="px-5 py-4 font-semibold">{t.qty}</td>
                  <td className="px-5 py-4 text-primary font-semibold">{t.discount}</td>
                  <td className="px-5 py-4 text-muted-foreground">
                    <ul className="space-y-1">
                      {t.perks.map((p) => (
                        <li key={p} className="flex items-center gap-1"><Check className="h-3 w-3 text-green-600" /> {p}</li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="max-w-3xl mx-auto px-4 sm:px-6 pb-16 w-full">
        <div className="bg-white border border-border rounded-2xl p-6 sm:p-8">
          <h2 className="font-display text-2xl text-primary">Request a quote</h2>
          <p className="text-sm text-muted-foreground mt-1">Tell us what you need — we'll come back with a curated proposal.</p>

          {submitted ? (
            <div className="mt-6 bg-green-50 border border-green-200 text-green-800 rounded-lg p-6 text-center">
              <Check className="h-8 w-8 mx-auto" />
              <p className="mt-2 font-semibold">Thanks, {form.contact.split(" ")[0] || "there"}!</p>
              <p className="text-sm mt-1">A gifting specialist will email {form.email} within one business day.</p>
              <Link to="/" className="mt-4 inline-block text-sm underline">Back home</Link>
            </div>
          ) : (
            <form onSubmit={submit} className="mt-6 grid sm:grid-cols-2 gap-4 text-sm">
              <Field label="Company *" value={form.company} onChange={(v) => setForm({ ...form, company: v })} />
              <Field label="Contact name *" value={form.contact} onChange={(v) => setForm({ ...form, contact: v })} />
              <Field label="Work email *" type="email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} />
              <Field label="Phone" type="tel" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} />
              <div>
                <label className="text-xs text-muted-foreground">Quantity</label>
                <select value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} className="mt-1 w-full border border-border rounded-md px-3 py-2 bg-white">
                  {TIERS.map((t) => <option key={t.qty}>{t.qty}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-muted-foreground">Occasion</label>
                <select value={form.occasion} onChange={(e) => setForm({ ...form, occasion: e.target.value })} className="mt-1 w-full border border-border rounded-md px-3 py-2 bg-white">
                  <option>Client appreciation</option>
                  <option>Employee onboarding</option>
                  <option>Ramadan / Eid</option>
                  <option>Conference / Event</option>
                  <option>Holiday gifting</option>
                  <option>Other</option>
                </select>
              </div>
              <Field label="Budget" value={form.budget} onChange={(v) => setForm({ ...form, budget: v })} placeholder="SAR 5,000" />
              <Field label="Needed by" type="date" value={form.when} onChange={(v) => setForm({ ...form, when: v })} />
              <div className="sm:col-span-2">
                <label className="text-xs text-muted-foreground">Notes</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  rows={4}
                  placeholder="Anything specific — flavors, dietary needs, delivery cities…"
                  className="mt-1 w-full border border-border rounded-md px-3 py-2"
                />
              </div>
              <button type="submit" className="sm:col-span-2 bg-primary text-primary-foreground rounded-md py-3 font-semibold hover:bg-primary/90">
                Send request
              </button>
            </form>
          )}
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}

function Field({ label, value, onChange, type = "text", placeholder }: { label: string; value: string; onChange: (v: string) => void; type?: string; placeholder?: string }) {
  return (
    <div>
      <label className="text-xs text-muted-foreground">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full border border-border rounded-md px-3 py-2"
      />
    </div>
  );
}
