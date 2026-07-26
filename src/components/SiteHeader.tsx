import { Link } from "@tanstack/react-router";
import { ChevronDown, Heart, MapPin, Menu, Search, ShoppingBag, User } from "lucide-react";
import { useState } from "react";
import { useStore, selectCartCount } from "@/lib/store";
import { CartDrawer } from "./CartDrawer";
import { MegaMenu } from "./MegaMenu";
import { useLang, setLang, useT } from "@/lib/i18n";

export function SiteHeader({ variant = "cream" }: { variant?: "cream" | "white" }) {
  const count = useStore(selectCartCount);
  const wishCount = useStore((s) => s.wishlist.length);
  const user = useStore((s) => s.user);
  const [open, setOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const lang = useLang();
  const t = useT();
  const bg = variant === "white" ? "bg-white" : "bg-background";

  return (
    <>
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-2 text-muted-foreground uppercase">
        {t("orderPickup")}
      </div>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      <header className={bg}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 grid grid-cols-3 items-center gap-2">
          <div className="flex items-center gap-2 sm:gap-4 text-sm justify-self-start min-w-0">

            <button
              onClick={() => setMenuOpen(true)}
              aria-label={t("menu")}
              className="h-9 w-9 rounded-full flex items-center justify-center hover:bg-secondary transition"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="relative">
              <button
                onClick={() => setLangOpen((v) => !v)}
                onBlur={() => setTimeout(() => setLangOpen(false), 150)}
                className="flex items-center gap-1 sm:gap-2 hover:text-primary transition"
              >
                <span className="text-base sm:text-lg">{lang === "ar" ? "🇸🇦" : "🇺🇸"}</span>
                <span className="hidden sm:inline">{lang === "ar" ? t("arabic") : t("english")}</span>
                <ChevronDown className="h-3 w-3" />

              </button>
              {langOpen && (
                <div className="absolute top-full mt-2 start-0 bg-white border border-border rounded-md shadow-md py-1 min-w-32 z-30">
                  <button
                    className={`block w-full text-start px-3 py-1.5 text-sm hover:bg-secondary ${lang === "en" ? "font-semibold" : ""}`}
                    onMouseDown={() => { setLang("en"); setLangOpen(false); }}
                  >
                    🇺🇸 English
                  </button>
                  <button
                    className={`block w-full text-start px-3 py-1.5 text-sm hover:bg-secondary ${lang === "ar" ? "font-semibold" : ""}`}
                    onMouseDown={() => { setLang("ar"); setLangOpen(false); }}
                  >
                    🇸🇦 العربية
                  </button>
                </div>
              )}
            </div>
            <span className="hidden md:inline-flex items-center gap-1 text-xs text-muted-foreground">
              <MapPin className="h-4 w-4" />
              <span>🇸🇦 Riyadh</span>
            </span>
          </div>
          <Link to="/" className="font-script text-2xl sm:text-3xl text-primary leading-none justify-self-center text-center whitespace-nowrap">
            Terrific<br /><span className="ms-6">Bites</span>
          </Link>
          <div className="flex items-center gap-3 sm:gap-5 text-sm justify-self-end">

            <Link to="/shop" aria-label="Search" className="hover:text-primary transition">
              <Search className="h-4 w-4" />
            </Link>
            <Link to="/wishlist" aria-label="Wishlist" className="hover:text-primary transition relative">
              <Heart className="h-4 w-4" />
              {wishCount > 0 && (
                <span className="absolute -top-2 -end-2 h-4 min-w-4 px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold flex items-center justify-center">
                  {wishCount}
                </span>
              )}
            </Link>
            <Link to={user ? "/account" : "/login"} className="flex items-center gap-2 hover:text-primary transition">
              <User className="h-4 w-4" /> <span className="hidden sm:inline">{user?.name ? user.name.split(" ")[0] : t("myAccount")}</span>
            </Link>
            <button onClick={() => setOpen(true)} className="flex items-center gap-2 hover:text-primary transition relative">
              <ShoppingBag className="h-4 w-4" /> <span className="hidden sm:inline">{t("cart")}</span>
              {count > 0 && (
                <span className="absolute -top-2 -end-3 h-4 min-w-4 px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold flex items-center justify-center">
                  {count}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      <CartDrawer open={open} onClose={() => setOpen(false)} />
      <MegaMenu open={menuOpen} onClose={() => setMenuOpen(false)} />
    </>
  );
}
