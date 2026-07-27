import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  UserRound, MapPin, ShoppingCart, FileText, Calendar, Heart, Wallet, Plus,
  LogOut, Trash2, X, ChevronDown, Pencil, AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";
import { SiteHeader } from "@/components/SiteHeader";
import { SiteFooter } from "@/components/SiteFooter";
import { useStore, auth, addresses as addressStore, orders as orderStore, RIYADH_AREAS } from "@/lib/store";
import { OrderStatusTimeline } from "@/components/OrderStatusTimeline";
import { useT } from "@/lib/i18n";

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
  { key: "personal", labelKey: "accountMenuPersonal", icon: UserRound },
  { key: "address", labelKey: "accountMenuAddress", icon: MapPin },
  { key: "orders", labelKey: "accountMenuOrders", icon: ShoppingCart },
  { key: "invoices", labelKey: "accountMenuInvoices", icon: FileText },
  { key: "occasions", labelKey: "accountMenuOccasions", icon: Calendar },
  { key: "favorite", labelKey: "accountMenuFavorite", icon: Heart },
  { key: "wallet", labelKey: "accountMenuWallet", icon: Wallet },
] as const;


type MenuKey = typeof menu[number]["key"];

function AccountPage() {
  const t = useT();
  const navigate = useNavigate();
  const user = useStore((s) => s.user);
  const addresses = useStore((s) => s.addresses);
  const orders = useStore((s) => s.orders);
  const [active, setActive] = useState<MenuKey>("personal");
  const [profile, setProfile] = useState({ name: "", email: "", phone: "", birthDate: "" });
  const [showAddr, setShowAddr] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [addrForm, setAddrForm] = useState({ name: "", phone: "", area: "", address: "", extra: "" });

  useEffect(() => {
    if (user) setProfile({ name: user.name ?? "", email: user.email ?? "", phone: user.phone ?? "", birthDate: user.birthDate ?? "" });
  }, [user]);

  useEffect(() => {
    if (!user) navigate({ to: "/login" });
  }, [user, navigate]);

  if (!user) return null;

  const statusLabel = (status: string) =>
    status === "Delivered" ? t("accountStatusDelivered") : status === "Paid" ? t("accountStatusPaid") : t("accountStatusProcessing");

  const activeMenuItem = menu.find((m) => m.key === active);

  const saveProfile = () => {
    auth.updateProfile(profile);
    toast.success(t("accountToastProfileSaved"));
  };

  const saveAddress = () => {
    if (!addrForm.name || !addrForm.phone || !addrForm.address) return toast.error(t("accountToastCompleteAddress"));
    if (editId) {
      addressStore.update(editId, addrForm);
      toast.success(t("accountToastAddressUpdated"));
    } else {
      addressStore.add(addrForm);
      toast.success(t("accountToastAddressAdded"));
    }
    setAddrForm({ name: "", phone: "", area: "", address: "", extra: "" });
    setEditId(null);
    setShowAddr(false);
  };

  const openAdd = () => {
    setEditId(null);
    setAddrForm({ name: "", phone: "", area: "", address: "", extra: "" });
    setShowAddr(true);
  };

  const openEdit = (id: string) => {
    const a = addresses.find((x) => x.id === id);
    if (!a) return;
    setEditId(id);
    setAddrForm({ name: a.name, phone: a.phone, area: a.area, address: a.address, extra: a.extra ?? "" });
    setShowAddr(true);
  };

  const confirmDelete = () => {
    if (!deleteId) return;
    addressStore.remove(deleteId);
    setDeleteId(null);
    toast.success(t("accountToastAddressRemoved"));
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <SiteHeader />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-14">
        <h1 className="font-display text-4xl text-primary text-center mb-2">{t("accountPageTitle")}</h1>
        <p className="text-center text-sm text-muted-foreground mb-10">
          {t("accountWelcomeBack").replace("{{name}}", user.name ?? user.email ?? t("accountFriendFallback"))}
        </p>

        <div className="grid md:grid-cols-[320px_1fr] gap-6">
          <aside className="bg-white rounded-2xl shadow-sm p-4 h-fit">
            <ul className="space-y-1">
              {menu.map(({ key, labelKey, icon: Icon }) => {
                const isActive = active === key;
                return (
                  <li key={key}>
                    <button
                      onClick={() => setActive(key)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition ${
                        isActive ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-secondary"
                      }`}
                    >
                      <Icon className="h-5 w-5" /><span>{t(labelKey)}</span>
                    </button>
                  </li>
                );
              })}
              <li className="pt-2 border-t border-border mt-2">
                <button
                  onClick={() => { navigate({ to: "/", replace: true }); auth.signOut(); toast.success(t("accountToastSignedOut")); }}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm text-destructive hover:bg-destructive/10"
                >
                  <LogOut className="h-5 w-5" /> {t("accountSignOut")}
                </button>
              </li>
            </ul>
          </aside>

          <section className="bg-white rounded-2xl shadow-sm p-8 min-h-[520px]">
            {active === "personal" && (
              <>
                <h2 className="text-sm font-semibold mb-6">{t("accountPersonalDetailsHeading")}</h2>
                <div className="grid md:grid-cols-2 gap-5">
                  <Field label={t("accountFieldFullName")} value={profile.name} onChange={(v) => setProfile({ ...profile, name: v })} />
                  <Field label={t("accountFieldEmail")} type="email" value={profile.email} onChange={(v) => setProfile({ ...profile, email: v })} />
                  <Field label={t("accountFieldMobile")} type="tel" value={profile.phone} onChange={(v) => setProfile({ ...profile, phone: v })} />
                  <Field label={t("accountFieldDob")} type="date" value={profile.birthDate} onChange={(v) => setProfile({ ...profile, birthDate: v })} />
                </div>
                <button onClick={saveProfile} className="mt-8 bg-primary text-primary-foreground rounded-md px-8 py-3 text-sm">{t("accountSaveChanges")}</button>
              </>
            )}

            {active === "address" && (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold">{t("accountSavedAddressesHeading").replace("{{count}}", String(addresses.length))}</h2>
                </div>
                <div className="space-y-3">
                  {addresses.map((a) => (
                    <div key={a.id} className={`border rounded-lg p-4 flex items-start justify-between gap-4 ${a.isDefault ? "border-primary bg-primary/5" : "border-border"}`}>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-medium">{a.name}</p>
                          {a.isDefault && <span className="text-[10px] uppercase tracking-wider bg-primary text-primary-foreground px-2 py-0.5 rounded-full">{t("accountDefaultBadge")}</span>}
                        </div>
                        <p className="text-xs text-muted-foreground">{a.phone}</p>
                        <p className="text-xs text-muted-foreground">{a.area}{a.address ? ` — ${a.address}` : ""}</p>
                        {a.extra && <p className="text-xs text-muted-foreground">{a.extra}</p>}
                        {!a.isDefault && !a.isGift && (
                          <button onClick={() => { addressStore.setDefault(a.id); toast.success(t("accountToastDefaultAddressUpdated")); }} className="mt-2 text-xs text-primary hover:underline">
                            {t("accountSetAsDefault")}
                          </button>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => openEdit(a.id)} className="p-1.5 text-foreground hover:text-primary hover:bg-secondary rounded-md transition" aria-label={t("accountAddressEditAriaLabel")}>
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button onClick={() => setDeleteId(a.id)} className="p-1.5 text-destructive hover:bg-destructive/10 rounded-md transition" aria-label={t("accountAddressDeleteAriaLabel")}>
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  onClick={openAdd}
                  className="mt-4 w-full border border-border rounded-lg py-5 flex items-center justify-center gap-2 text-sm text-foreground hover:border-primary hover:text-primary transition"
                >
                  <Plus className="h-5 w-5" /> {t("accountAddAddress")}
                </button>
              </>
            )}

            {active === "orders" && (
              <>
                <h2 className="text-sm font-semibold mb-4">{t("accountOrderHistoryHeading").replace("{{count}}", String(orders.length))}</h2>
                {orders.length === 0 ? (
                  <div className="text-center py-16">
                    <p className="text-sm text-muted-foreground">{t("accountNoOrdersYet")}</p>
                    <Link to="/chocolates" className="mt-4 inline-block text-sm text-primary underline">{t("accountStartShopping")}</Link>
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
                              {statusLabel(o.status)}
                            </span>
                          </div>
                        </div>
                        <OrderStatusTimeline order={o} compact />
                        <p className="mt-1 text-xs text-muted-foreground">
                          {o.items.map((i) => `${i.qty}× ${i.name}`).join(" · ")}
                        </p>
                        <div className="mt-2 flex items-center justify-between">
                          <p className="text-xs">{t("accountPaymentLabel")} {o.method}</p>
                          {o.status !== "Delivered" && (
                            <button
                              onClick={() => orderStore.advance(o.id)}
                              className="text-xs text-primary hover:underline"
                            >
                              {t("accountMarkAsPrefix")} {statusLabel(o.status === "Processing" ? "Paid" : "Delivered")}
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
                <h2 className="mt-3 font-display text-2xl text-primary">{t("accountFavoritesHeading")}</h2>
                <p className="text-sm text-muted-foreground mt-3 max-w-sm">{t("accountFavoritesDesc")}</p>
              </div>
            )}

            {active === "wallet" && <WalletPanel />}

            {(active === "invoices" || active === "occasions") && activeMenuItem && (
              <div className="h-full flex flex-col items-center justify-center text-center py-24">
                <h2 className="font-display text-2xl text-primary">{t(activeMenuItem.labelKey)}</h2>
                <p className="text-sm text-muted-foreground mt-3 max-w-sm">
                  {t("accountEmptyStateDesc").replace("{{label}}", t(activeMenuItem.labelKey))}
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
            <h3 className="font-semibold mb-4">{editId ? t("accountEditAddressHeading") : t("accountNewAddressHeading")}</h3>
            <div className="space-y-3">
              <input value={addrForm.name} onChange={(e) => setAddrForm({ ...addrForm, name: e.target.value })} placeholder={t("accountPlaceholderName")} className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
              <input value={addrForm.phone} onChange={(e) => setAddrForm({ ...addrForm, phone: e.target.value })} placeholder={t("accountPlaceholderPhone")} className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
              <div className="relative">
                <select value={addrForm.area} onChange={(e) => setAddrForm({ ...addrForm, area: e.target.value })} className="w-full appearance-none border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary bg-white">
                  <option value="">{t("accountSelectAreaOption")}</option>
                  {RIYADH_AREAS.map((a) => <option key={a} value={a}>{a}</option>)}
                </select>
                <ChevronDown className="h-4 w-4 absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none" />
              </div>
              <input value={addrForm.address} onChange={(e) => setAddrForm({ ...addrForm, address: e.target.value })} placeholder={t("accountPlaceholderStreetAddress")} className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
              <input value={addrForm.extra} onChange={(e) => setAddrForm({ ...addrForm, extra: e.target.value })} placeholder={t("accountPlaceholderAptFloor")} className="w-full border border-border rounded-md px-3 py-2 text-sm outline-none focus:border-primary" />
            </div>
            <button onClick={saveAddress} className="mt-4 w-full bg-primary text-primary-foreground rounded-md py-3 text-sm">{editId ? t("accountUpdateAddressButton") : t("accountSaveAddress")}</button>
          </div>
        </div>
      )}

      {deleteId && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6 text-center relative">
            <button onClick={() => setDeleteId(null)} className="absolute top-4 right-4"><X className="h-5 w-5" /></button>
            <div className="mx-auto w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
              <AlertTriangle className="h-6 w-6 text-destructive" />
            </div>
            <h3 className="font-semibold mb-2">{t("accountDeleteAddressConfirmHeading")}</h3>
            <p className="text-sm text-muted-foreground mb-6">{t("accountDeleteAddressConfirmDesc")}</p>
            <div className="flex gap-3">
              <button onClick={() => setDeleteId(null)} className="flex-1 border border-border rounded-md py-2.5 text-sm hover:bg-secondary transition">{t("accountCancelButton")}</button>
              <button onClick={confirmDelete} className="flex-1 bg-destructive text-destructive-foreground rounded-md py-2.5 text-sm hover:opacity-90 transition">{t("accountDeleteButton")}</button>
            </div>
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
  const t = useT();
  const points = useStore((s) => s.loyaltyPoints);
  const history = useStore((s) => s.loyaltyHistory);
  const dollars = (points / 100).toFixed(2);
  return (
    <div className="py-6">
      <div className="rounded-2xl bg-gradient-to-br from-primary to-primary/70 text-primary-foreground p-6 text-center">
        <Wallet className="h-8 w-8 mx-auto opacity-90" />
        <p className="mt-2 text-xs uppercase tracking-widest opacity-80">{t("accountWalletPointsLabel")}</p>
        <p className="mt-1 font-display text-4xl">{points}</p>
        <p className="mt-1 text-xs opacity-80">{t("accountWalletRewardValue").replace("{{dollars}}", dollars)}</p>
        <p className="mt-3 text-[11px] opacity-70">{t("accountWalletEarnRule")}</p>
      </div>
      <h3 className="mt-6 text-sm font-semibold">{t("accountWalletActivityHeading")}</h3>
      {history.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">{t("accountWalletNoActivity")}</p>
      ) : (
        <ul className="mt-3 divide-y divide-border">
          {history.slice(0, 20).map((h) => (
            <li key={h.id} className="flex items-center justify-between py-3 text-sm">
              <div>
                <p className="font-medium">{h.note}</p>
                <p className="text-xs text-muted-foreground">{new Date(h.at).toLocaleString()}</p>
              </div>
              <span className={h.type === "earn" ? "text-primary font-semibold" : "text-muted-foreground"}>
                {h.type === "earn" ? "+" : "−"}{h.points} {t("accountWalletPtsSuffix")}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
