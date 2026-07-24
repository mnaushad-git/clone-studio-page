import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  UserRound, MapPin, ShoppingCart, DollarSign, FileText, Calendar, Heart, Wallet, Plus,
  LogOut, Trash2, X,
} from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { useStore, auth, addresses as addressStore, orders as orderStore } from "@/lib/store";
import { OrderStatusTimeline } from "@/components/OrderStatusTimeline";

export const Route = createFileRoute("/account")({
  component: AccountPage,
  head: () => ({
    meta: [
      { title: "My Account — Terrific Bites" },
      { name: "description", content: "Manage your Terrific Bites profile, addresses, orders and rewards." },
      { property: "og:title", content: "My Account — Terrific Bites" },
      { property: "og:description", content: "Manage your profile, addresses and orders." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "robots", content: "noindex" },
    ],
  }),
});

const menu = [
  { key: "personal", label: "My Personal Information", icon: UserRound },
  { key: "address", label: "My Address", icon: MapPin },
  { key: "orders", label: "My Orders", icon: ShoppingCart },
  { key: "subs", label: "My Subscriptions", icon: DollarSign },
  { key: "invoices", label: "Invoices", icon: FileText },
  { key: "occasions", label: "My Occasions", icon: Calendar },
  { key: "favorite", label: "Favorite", icon: Heart },
  { key: "wallet", label: "Terrific Wallet", icon: Wallet },
] as const;

type MenuKey = typeof menu[number]["key"];

function AccountPage() {
  const navigate = useNavigate();
  const user = useStore((s) => s.user);
  const addresses = useStore((s) => s.addresses);
  const orders = useStore((s) => s.orders);
  const [active, setActive] = useState<MenuKey>("personal");
  const [profile, setProfile] = useState({ name: "", email: "", phone: "", birthDate: "" });
  const [showAddr, setShowAddr] = useState(false);
  const [newAddr, setNewAddr] = useState({ name: "", phone: "", area: "", address: "", extra: "" });

  useEffect(() => {
    if (user) setProfile({ name: user.name ?? "", email: user.email ?? "", phone: user.phone ?? "", birthDate: user.birthDate ?? "" });
  }, [user]);

  useEffect(() => {
    if (!user) navigate({ to: "/login" });
  }, [user, navigate]);

  if (!user) return null;

  const saveProfile = () => {
    auth.updateProfile(profile);
    toast.success("Profile saved");
  };

  const addAddress = () => {
    if (!newAddr.name || !newAddr.phone || !newAddr.address) return toast.error("Please complete address");
    addressStore.add(newAddr);
    setNewAddr({ name: "", phone: "", area: "", address: "", extra: "" });
    setShowAddr(false);
    toast.success("Address added");
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-14">
        <h1 className="font-display text-4xl text-primary text-center mb-2">My Account</h1>
        <p className="text-center text-sm text-muted-foreground mb-10">Welcome back, {user.name ?? user.email ?? "friend"}!</p>

        <div className="grid md:grid-cols-[320px_1fr] gap-6">
          <aside className="bg-white rounded-2xl shadow-sm p-4 h-fit">
            <ul className="space-y-1">
              {menu.map(({ key, label, icon: Icon }) => {
                const isActive = active === key;
                return (
                  <li key={key}>
                    <button
                      onClick={() => setActive(key)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition ${
                        isActive ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-secondary"
                      }`}
                    >
                      <Icon className="h-5 w-5" /><span>{label}</span>
                    </button>
                  </li>
                );
              })}
              <li className="pt-2 border-t border-border mt-2">
                <button
                  onClick={() => { auth.signOut(); toast.success("Signed out"); navigate({ to: "/" }); }}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm text-destructive hover:bg-destructive/10"
                >
                  <LogOut className="h-5 w-5" /> Sign Out
                </button>
              </li>
            </ul>
          </aside>

          <section className="bg-white rounded-2xl shadow-sm p-8 min-h-[520px]">
            {active === "personal" && (
              <>
                <h2 className="text-sm font-semibold mb-6">Personal details</h2>
                <div className="grid md:grid-cols-2 gap-5">
                  <Field label="Full name" value={profile.name} onChange={(v) => setProfile({ ...profile, name: v })} />
                  <Field label="Email" type="email" value={profile.email} onChange={(v) => setProfile({ ...profile, email: v })} />
                  <Field label="Mobile number" type="tel" value={profile.phone} onChange={(v) => setProfile({ ...profile, phone: v })} />
                  <Field label="Date of birth" type="date" value={profile.birthDate} onChange={(v) => setProfile({ ...profile, birthDate: v })} />
                </div>
                <button onClick={saveProfile} className="mt-8 bg-primary text-primary-foreground rounded-md px-8 py-3 text-sm">Save Changes</button>
              </>
            )}

            {active === "address" && (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold">Saved Addresses ({addresses.length})</h2>
                </div>
                <div className="space-y-3">
                  {addresses.map((a) => (
                    <div key={a.id} className="border border-border rounded-lg p-4 flex items-start justify-between gap-4">
                      <div>
                        <p className="font-medium">{a.name}</p>
                        <p className="text-xs text-muted-foreground">{a.phone}</p>
                        <p className="text-xs text-muted-foreground">{a.area}{a.address ? ` — ${a.address}` : ""}</p>
                        {a.extra && <p className="text-xs text-muted-foreground">{a.extra}</p>}
                      </div>
                      <button onClick={() => { addressStore.remove(a.id); toast.success("Address removed"); }} className="text-destructive hover:opacity-70" aria-label="Delete">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setShowAddr(true)}
                  className="mt-4 w-full border border-border rounded-lg py-5 flex items-center justify-center gap-2 text-sm text-foreground hover:border-primary hover:text-primary transition"
                >
                  <Plus className="h-5 w-5" /> Add Address
                </button>
              </>
            )}

            {active === "orders" && (
              <>
                <h2 className="text-sm font-semibold mb-4">Order History ({orders.length})</h2>
                {orders.length === 0 ? (
                  <div className="text-center py-16">
                    <p className="text-sm text-muted-foreground">No orders yet.</p>
                    <Link to="/chocolates" className="mt-4 inline-block text-sm text-primary underline">Start shopping</Link>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {orders.map((o) => (
                      <div key={o.id} className="border border-border rounded-lg p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-semibold text-sm">#{o.id}</p>
                            <p className="text-xs text-muted-foreground">{new Date(o.createdAt).toLocaleString()}</p>
                          </div>
                          <div className="text-right">
                            <p className="font-semibold">SAR {o.total.toFixed(2)}</p>
                            <span
                              className={`inline-block mt-1 text-[10px] px-2 py-0.5 rounded-full font-medium ${
                                o.status === "Delivered"
                                  ? "bg-primary/15 text-primary"
                                  : o.status === "Paid"
                                  ? "bg-secondary text-foreground"
                                  : "bg-amber-100 text-amber-800"
                              }`}
                            >
                              {o.status}
                            </span>
                          </div>
                        </div>
                        <OrderStatusTimeline order={o} compact />
                        <p className="mt-1 text-xs text-muted-foreground">
                          {o.items.map((i) => `${i.qty}× ${i.name}`).join(" · ")}
                        </p>
                        <div className="mt-2 flex items-center justify-between">
                          <p className="text-xs">Payment: {o.method}</p>
                          {o.status !== "Delivered" && (
                            <button
                              onClick={() => orderStore.advance(o.id)}
                              className="text-xs text-primary hover:underline"
                            >
                              Mark as {o.status === "Processing" ? "Paid" : "Delivered"}
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {active === "favorite" && (
              <div className="h-full flex flex-col items-center justify-center text-center py-24">
                <Heart className="h-10 w-10 text-primary" />
                <h2 className="mt-3 font-display text-2xl text-primary">Favorites</h2>
                <p className="text-sm text-muted-foreground mt-3 max-w-sm">Save your favorite desserts here for quick reordering.</p>
              </div>
            )}

            {active === "wallet" && <WalletPanel />}

            {(active === "subs" || active === "invoices" || active === "occasions") && (
              <div className="h-full flex flex-col items-center justify-center text-center py-24">
                <h2 className="font-display text-2xl text-primary">{menu.find((m) => m.key === active)?.label}</h2>
                <p className="text-sm text-muted-foreground mt-3 max-w-sm">
                  Nothing here yet. Your {menu.find((m) => m.key === active)?.label.toLowerCase()} will appear in this space.
                </p>
              </div>
            )}
          </section>
        </div>
      </main>

      {showAddr && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 relative">
            <button onClick={() => setShowAddr(false)} className="absolute top-4 right-4"><X className="h-5 w-5" /></button>
            <h3 className="font-semibold mb-4">New Address</h3>
            <div className="space-y-3">
              <input value={newAddr.name} onChange={(e) => setNewAddr({ ...newAddr, name: e.target.value })} placeholder="Name" className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
              <input value={newAddr.phone} onChange={(e) => setNewAddr({ ...newAddr, phone: e.target.value })} placeholder="Phone" className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
              <input value={newAddr.area} onChange={(e) => setNewAddr({ ...newAddr, area: e.target.value })} placeholder="City / Area" className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
              <input value={newAddr.address} onChange={(e) => setNewAddr({ ...newAddr, address: e.target.value })} placeholder="Street address" className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
              <input value={newAddr.extra} onChange={(e) => setNewAddr({ ...newAddr, extra: e.target.value })} placeholder="Apt / floor / landmark (optional)" className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
            </div>
            <button onClick={addAddress} className="mt-4 w-full bg-primary text-primary-foreground rounded-md py-3 text-sm">Save Address</button>
          </div>
        </div>
      )}

      <SiteFooter />
    </div>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return (
    <div>
      <label className="block text-xs font-semibold mb-2">{label}</label>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="w-full border border-border rounded-md px-4 py-3 text-sm outline-none focus:border-primary bg-transparent" />
    </div>
  );
}

function WalletPanel() {
  const points = useStore((s) => s.loyaltyPoints);
  const history = useStore((s) => s.loyaltyHistory);
  const dollars = (points / 100).toFixed(2);
  return (
    <div className="py-6">
      <div className="rounded-2xl bg-gradient-to-br from-primary to-primary/70 text-primary-foreground p-6 text-center">
        <Wallet className="h-8 w-8 mx-auto opacity-90" />
        <p className="mt-2 text-xs uppercase tracking-widest opacity-80">Terrific Points</p>
        <p className="mt-1 font-display text-4xl">{points}</p>
        <p className="mt-1 text-xs opacity-80">≈ SAR {dollars} reward value</p>
        <p className="mt-3 text-[11px] opacity-70">Earn 1 point per SAR 1 spent. 100 points = SAR 1 off.</p>
      </div>
      <h3 className="mt-6 text-sm font-semibold">Activity</h3>
      {history.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">No activity yet — place an order to earn points.</p>
      ) : (
        <ul className="mt-3 divide-y divide-border">
          {history.slice(0, 20).map((h) => (
            <li key={h.id} className="flex items-center justify-between py-3 text-sm">
              <div>
                <p className="font-medium">{h.note}</p>
                <p className="text-xs text-muted-foreground">{new Date(h.at).toLocaleString()}</p>
              </div>
              <span className={h.type === "earn" ? "text-primary font-semibold" : "text-muted-foreground"}>
                {h.type === "earn" ? "+" : "−"}{h.points} pts
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
