import { Link } from "@tanstack/react-router";
import { ChevronDown, ShoppingBag, User } from "lucide-react";
import { useState } from "react";
import { useStore, selectCartCount } from "@/lib/store";
import { CartDrawer } from "./CartDrawer";

export function SiteHeader({ variant = "cream" }: { variant?: "cream" | "white" }) {
  const count = useStore(selectCartCount);
  const user = useStore((s) => s.user);
  const [open, setOpen] = useState(false);
  const bg = variant === "white" ? "bg-white" : "bg-background";

  return (
    <>
      <div className="bg-white text-center text-[11px] tracking-[0.2em] py-2 text-muted-foreground uppercase">
        Order Desserts for Local Pickup
      </div>
      <div className="h-8 zigzag-top" style={{ ["--c" as string]: "white" }} />

      <header className={bg}>
        <div className="max-w-7xl mx-auto px-6 py-4 grid grid-cols-3 items-center">
          <div className="flex items-center gap-2 text-sm justify-self-start">
            <span className="text-lg">🇺🇸</span>
            <span>English</span>
            <ChevronDown className="h-3 w-3" />
          </div>
          <Link to="/" className="font-script text-3xl text-primary leading-none justify-self-center text-center">
            Terrific<br /><span className="ml-6">Bites</span>
          </Link>
          <div className="flex items-center gap-6 text-sm justify-self-end">
            <Link to={user ? "/account" : "/login"} className="flex items-center gap-2 hover:text-primary transition">
              <User className="h-4 w-4" /> {user?.name ? user.name.split(" ")[0] : "My Account"}
            </Link>
            <button onClick={() => setOpen(true)} className="flex items-center gap-2 hover:text-primary transition relative">
              <ShoppingBag className="h-4 w-4" /> Cart
              {count > 0 && (
                <span className="absolute -top-2 -right-3 h-4 min-w-4 px-1 rounded-full bg-primary text-primary-foreground text-[10px] font-semibold flex items-center justify-center">
                  {count}
                </span>
              )}
            </button>
          </div>
        </div>
      </header>

      <CartDrawer open={open} onClose={() => setOpen(false)} />
    </>
  );
}
