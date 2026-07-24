import { Facebook, Instagram, Twitter, Youtube } from "lucide-react";
import logoFooter from "@/assets/logo-footer.png.asset.json";

export function SiteFooter() {
  return (
    <>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "var(--brand)" }} />
      <footer className="bg-primary text-primary-foreground">
        <div className="max-w-7xl mx-auto px-6 py-14 grid md:grid-cols-4 gap-10">
          <div>
            <img src={logoFooter.url} alt="Terrific Bites" className="h-16 w-auto object-contain" />
            <p className="mt-4 text-xs opacity-80 max-w-xs">Handcrafted cupcakes, donuts and desserts baked fresh daily. Made with love in our neighborhood bakery.</p>
            <div className="flex gap-3 mt-5">
              {[Facebook, Instagram, Twitter, Youtube].map((I, i) => (
                <a key={i} href="#" className="h-7 w-7 rounded-full bg-background/10 flex items-center justify-center hover:bg-background/20"><I className="h-3.5 w-3.5" /></a>
              ))}
            </div>
          </div>
          {[
            { title: "Shop", items: ["Cupcakes", "Cakes", "Chocolates", "Donuts"] },
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
            <span>Copyright © 2024 Terrific Bites. All Rights Reserved</span>
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
