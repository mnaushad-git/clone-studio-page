import { createFileRoute, Outlet, Link, useRouterState, useNavigate, redirect } from "@tanstack/react-router";
import { useState } from "react";
import {
  LayoutDashboard, Package, ShoppingBag, Users, Tags, Ticket, Truck, Image as ImageIcon,
  Star, Gift, Settings, UserCog, BarChart3, Bell, LogOut, Menu, X, Home, Palette,
} from "lucide-react";
import { useAdmin, adminAuth, notificationStore } from "@/lib/admin-store";

export const Route = createFileRoute("/admin")({
  beforeLoad: ({ location }) => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem("tb.admin.v1");
      const session = raw ? JSON.parse(raw)?.adminSession : null;
      if (!session && location.pathname !== "/admin/login") {
        throw redirect({ to: "/admin/login" });
      }
    } catch (e) {
      if ((e as any)?.isRedirect) throw e;
    }
  },
  component: AdminLayout,
  head: () => ({ meta: [{ title: "Admin — Terrific Bites" }, { name: "robots", content: "noindex" }] }),
});

type NavItem = { to: string; label: string; icon: React.ComponentType<{ className?: string }> };
const NAV: NavItem[] = [
  { to: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { to: "/admin/orders", label: "Orders", icon: ShoppingBag },
  { to: "/admin/products", label: "Products", icon: Package },
  { to: "/admin/categories", label: "Categories", icon: Tags },
  { to: "/admin/customers", label: "Customers", icon: Users },
  { to: "/admin/promotions", label: "Promotions", icon: Ticket },
  { to: "/admin/delivery", label: "Delivery", icon: Truck },
  { to: "/admin/content", label: "Content", icon: ImageIcon },
  { to: "/admin/reviews", label: "Reviews", icon: Star },
  { to: "/admin/loyalty", label: "Loyalty", icon: Gift },
  { to: "/admin/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/admin/staff", label: "Staff & Roles", icon: UserCog },
  { to: "/admin/theme", label: "Theme", icon: Palette },
  { to: "/admin/settings", label: "Settings", icon: Settings },
];

function AdminLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const session = useAdmin((s) => s.adminSession);
  const notifications = useAdmin((s) => s.notifications);
  const unread = notifications.filter((n) => !n.read).length;
  const [open, setOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);

  // Login page: render without chrome
  if (pathname === "/admin/login") return <Outlet />;

  return (
    <div className="min-h-screen bg-cream flex">
      {/* Sidebar */}
      <aside className={`${open ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0 fixed lg:static inset-y-0 left-0 z-40 w-64 bg-primary text-primary-foreground flex flex-col transition-transform`}>
        <div className="h-16 px-5 flex items-center justify-between border-b border-white/10">
          <Link to="/admin" className="font-display text-lg tracking-wide">Terrific · Admin</Link>
          <button className="lg:hidden" onClick={() => setOpen(false)}><X className="h-5 w-5" /></button>
        </div>
        <nav className="flex-1 overflow-y-auto py-3">
          {NAV.map((item) => {
            const active = item.to === "/admin" ? pathname === "/admin" : pathname.startsWith(item.to);
            const Icon = item.icon;
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${active ? "bg-white/10 text-white border-l-2 border-amber-300" : "text-primary-foreground/70 hover:bg-white/5 hover:text-white"}`}
              >
                <Icon className="h-4 w-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-white/10 text-xs text-primary-foreground/70">
          <div className="mb-2">
            <div className="text-white font-medium">{session?.email ?? "—"}</div>
            <div className="capitalize">{session?.role ?? "guest"}</div>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/" className="flex-1 flex items-center justify-center gap-1 rounded bg-white/10 hover:bg-white/20 py-1.5"><Home className="h-3 w-3" /> Store</Link>
            <button
              onClick={() => { adminAuth.signOut(); navigate({ to: "/admin/login" }); }}
              className="flex-1 flex items-center justify-center gap-1 rounded bg-white/10 hover:bg-white/20 py-1.5"
            ><LogOut className="h-3 w-3" /> Sign out</button>
          </div>
        </div>
      </aside>


      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 bg-white border-b flex items-center justify-between px-4 lg:px-8 sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <button className="lg:hidden" onClick={() => setOpen(true)}><Menu className="h-5 w-5" /></button>
            <h1 className="font-display text-lg text-stone-800">
              {NAV.find((n) => (n.to === "/admin" ? pathname === "/admin" : pathname.startsWith(n.to)))?.label ?? "Admin"}
            </h1>
          </div>
          <div className="relative">
            <button onClick={() => setNotifOpen((v) => !v)} className="relative p-2 rounded-full hover:bg-stone-100">
              <Bell className="h-5 w-5 text-stone-700" />
              {unread > 0 && <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-500" />}
            </button>
            {notifOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-white border rounded-lg shadow-lg overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3 border-b">
                  <span className="font-medium text-sm">Notifications</span>
                  <button onClick={() => notificationStore.markAllRead()} className="text-xs text-stone-500 hover:text-stone-800">Mark all read</button>
                </div>
                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 && <div className="px-4 py-6 text-sm text-stone-500 text-center">No notifications</div>}
                  {notifications.map((n) => (
                    <button key={n.id} onClick={() => notificationStore.markRead(n.id)} className={`w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-stone-50 ${!n.read ? "bg-amber-50/50" : ""}`}>
                      <div className="text-sm font-medium text-stone-800">{n.title}</div>
                      <div className="text-xs text-stone-600 mt-0.5">{n.body}</div>
                      <div className="text-[10px] text-stone-400 mt-1">{new Date(n.at).toLocaleString()}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </header>
        <main className="flex-1 p-4 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
