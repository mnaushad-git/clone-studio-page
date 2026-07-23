import { Link } from "@tanstack/react-router";
import { X } from "lucide-react";
import { useT } from "@/lib/i18n";
import moments from "@/assets/hero-cupcake.jpg";
import recipients from "@/assets/gift-cream.jpg";
import cakes from "@/assets/cake-main.jpg";
import chocolates from "@/assets/choc-1.jpg";
import donuts from "@/assets/donuts-hero.jpg";
import gifts from "@/assets/gift-donuts.jpg";

export function MegaMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useT();

  const tiles = [
    { label: t("moments"), img: moments, to: "/chocolates" as const },
    { label: t("recipients"), img: recipients, to: "/chocolates" as const },
  ];

  const rows = [
    { label: t("cakes"), img: cakes, to: "/chocolates" as const },
    { label: t("chocolates"), img: chocolates, to: "/chocolates" as const },
    { label: t("donuts"), img: donuts, to: "/chocolates" as const },
    { label: t("gifts"), img: gifts, to: "/chocolates" as const },
  ];

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/40 transition-opacity ${open ? "opacity-100" : "opacity-0 pointer-events-none"}`}
        onClick={onClose}
      />
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-full max-w-md bg-background shadow-xl transition-transform duration-300 ${open ? "translate-x-0" : "-translate-x-full"} overflow-y-auto`}
        aria-hidden={!open}
      >
        <div className="flex items-center justify-between px-6 py-5">
          <h2 className="font-display text-3xl text-primary">{t("explore")}</h2>
          <button
            onClick={onClose}
            aria-label={t("close")}
            className="h-9 w-9 rounded-full border border-border flex items-center justify-center hover:bg-secondary transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-6 grid grid-cols-2 gap-3">
          {tiles.map((tile) => (
            <Link
              key={tile.label}
              to={tile.to}
              onClick={onClose}
              className="relative aspect-[3/4] rounded-lg overflow-hidden group"
            >
              <img src={tile.img} alt={tile.label} className="absolute inset-0 h-full w-full object-cover group-hover:scale-105 transition-transform duration-500" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
              <span className="absolute inset-x-0 bottom-4 text-center text-white font-display text-lg tracking-wide">
                {tile.label}
              </span>
            </Link>
          ))}
        </div>

        <div className="px-6 py-6 space-y-3">
          {rows.map((row) => (
            <Link
              key={row.label}
              to={row.to}
              onClick={onClose}
              className="flex items-center justify-between bg-cream rounded-lg px-5 py-3 hover:bg-secondary transition"
            >
              <span className="font-display text-primary text-lg">
                {row.label} <span className="ms-2">→</span>
              </span>
              <img src={row.img} alt="" className="h-14 w-14 rounded-md object-cover" />
            </Link>
          ))}
        </div>

        <div className="px-6 pb-8 border-t border-border pt-6">
          <Link to="/about" onClick={onClose} className="block py-2 text-primary hover:underline">
            {t("aboutUs")}
          </Link>
          <Link to="/login" onClick={onClose} className="block py-2 text-primary hover:underline">
            {t("signIn")}
          </Link>
        </div>
      </aside>
    </>
  );
}
