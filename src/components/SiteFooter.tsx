import { Facebook, Instagram, Twitter, Music2, Mail, Phone } from "lucide-react";
import logoFooter from "@/assets/logo-footer.png.asset.json";
import { useAdmin } from "@/lib/admin-store";

export function SiteFooter() {
  const settings = useAdmin((s) => s.settings);
  const categories = useAdmin((s) => s.categories);
  const socials = settings.socials || {};

  const visibleCats = [...categories].filter((c) => c.visible).sort((a, b) => a.order - b.order).slice(0, 6);

  const socialLinks: { href: string; Icon: typeof Facebook; label: string }[] = [];
  if (socials.facebook) socialLinks.push({ href: socials.facebook, Icon: Facebook, label: "Facebook" });
  if (socials.instagram) socialLinks.push({ href: `https://instagram.com/${socials.instagram.replace(/^@/, "")}`, Icon: Instagram, label: "Instagram" });
  if (socials.twitter) socialLinks.push({ href: `https://twitter.com/${socials.twitter.replace(/^@/, "")}`, Icon: Twitter, label: "Twitter" });
  if (socials.tiktok) socialLinks.push({ href: `https://tiktok.com/@${socials.tiktok.replace(/^@/, "")}`, Icon: Music2, label: "TikTok" });

  return (
    <>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "var(--brand)" }} />
      <footer className="bg-primary text-primary-foreground">
        <div className="max-w-7xl mx-auto px-6 py-14 grid md:grid-cols-4 gap-10">
          <div>
            <img src={logoFooter.url} alt={settings.brandName} className="h-16 w-auto object-contain" />
            <p className="mt-4 text-xs opacity-80 max-w-xs">Handcrafted cupcakes, donuts and desserts baked fresh daily. Made with love in our neighborhood bakery.</p>
            <div className="mt-4 space-y-1 text-xs opacity-80">
              {settings.supportEmail && <p className="flex items-center gap-1.5"><Mail className="h-3.5 w-3.5" /> {settings.supportEmail}</p>}
              {settings.supportPhone && <p className="flex items-center gap-1.5"><Phone className="h-3.5 w-3.5" /> {settings.supportPhone}</p>}
            </div>
            {socialLinks.length > 0 && (
              <div className="flex gap-3 mt-5">
                {socialLinks.map(({ href, Icon, label }) => (
                  <a key={label} href={href} aria-label={label} target="_blank" rel="noreferrer" className="h-7 w-7 rounded-full bg-background/10 flex items-center justify-center hover:bg-background/20"><Icon className="h-3.5 w-3.5" /></a>
                ))}
              </div>
            )}
          </div>
          <div>
            <h4 className="font-display uppercase text-sm tracking-wider mb-4">Shop</h4>
            <ul className="space-y-2 text-xs opacity-80">
              {visibleCats.map((c) => <li key={c.id}><a href={`/${c.slug}`} className="hover:opacity-100">{c.label}</a></li>)}
            </ul>
          </div>
          {[
            { title: "Company", items: ["About Us", "Careers", "Press", "Contact"] },
            { title: "Help", items: ["Delivery", "Returns", "FAQ", "Support"] },
          ].map(col => (
            <div key={col.title}>
              <h4 className="font-display uppercase text-sm tracking-wider mb-4">{col.title}</h4>
              <ul className="space-y-2 text-xs opacity-80">
                {col.items.map(i => <li key={i}><a href="#" className="hover:opacity-100">{i}</a></li>)}
              </ul>
            </div>
          ))}
        </div>
        <div className="border-t border-primary-foreground/10">
          <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap justify-between items-center gap-4 text-[11px] opacity-70">
            <span>Copyright © {new Date().getFullYear()} {settings.brandName}. All Rights Reserved</span>
            <div className="flex gap-2">
              {["VISA","AMEX","PayPal","GPay"].map(p => (
                <span key={p} className="bg-background text-primary rounded px-2 py-1 text-[10px] font-semibold">{p}</span>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </>
  );
}
