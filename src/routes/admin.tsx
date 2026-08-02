import {
  createFileRoute,
  Outlet,
  Link,
  useRouterState,
  useNavigate,
  redirect,
} from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  LayoutDashboard,
  Package,
  ShoppingBag,
  Users,
  Tags,
  Ticket,
  Truck,
  Image as ImageIcon,
  Star,
  Gift,
  Settings,
  UserCog,
  BarChart3,
  Bell,
  LogOut,
  Menu,
  X,
  Home,
  Palette,
  ClipboardList,
  Activity,
} from "lucide-react";
import { useAdmin, notificationStore } from "@/lib/admin-store";
import { fetchMe, logout, useAdminMe, useSystemStatus, type AdminUserOut } from "@/lib/admin-api";

export const Route = createFileRoute("/admin")({
  beforeLoad: async ({ location, context }) => {
    if (location.pathname === "/admin/login") return;
    // Server-side render has no access to the browser's httpOnly session cookies
    // (this route's own `fetch` calls don't forward the incoming request's Cookie
    // header) — checking auth here during SSR would always look unauthenticated and
    // wrongly redirect a logged-in admin on every hard refresh. Skip it server-side;
    // AdminLayout's client-side effect below is the real guard once hydrated, same
    // two-layer shape the previous localStorage-based guard used.
    if (typeof window === "undefined") return;
    try {
      await context.queryClient.ensureQueryData({
        queryKey: ["admin", "me"],
        queryFn: fetchMe,
        staleTime: 60_000,
      });
    } catch {
      throw redirect({ to: "/admin/login" });
    }
  },
  component: AdminLayout,
  head: () => ({
    meta: [{ title: "Admin — Terrific Bites" }, { name: "robots", content: "noindex" }],
  }),
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
  { to: "/admin/audit", label: "Audit Log", icon: ClipboardList },
  { to: "/admin/system", label: "System Status", icon: Activity },
  { to: "/admin/theme", label: "Theme", icon: Palette },
  { to: "/admin/settings", label: "Settings", icon: Settings },
];

function OperationalBanner() {
  const { data: status } = useSystemStatus();
  if (!status?.stub_providers_active) return null;
  return (
    <div className="bg-amber-500 text-black text-center text-xs py-2 font-medium px-4">
      Development mode: payments, Odoo order push, and notifications are using stub providers — no
      real charges, ERP orders, or emails/SMS are sent.
      {status.redis === "down" &&
        " Worker infrastructure (Redis) is unavailable — retry actions will queue but not run until it's back."}
    </div>
  );
}

function AdminLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: admin, isLoading, isError } = useAdminMe(pathname !== "/admin/login");
  const notifications = useAdmin((s) => s.notifications);
  const theme = useAdmin((s) => s.theme);
  const unread = notifications.filter((n) => !n.read).length;
  const [open, setOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);

  // Client-side fallback guard: beforeLoad can't check auth during SSR (see its
  // comment), so a hard refresh/direct navigation lands here first — once the /me
  // check actually resolves (client-side, real cookies attached), redirect if it
  // turned out the session isn't valid after all.
  useEffect(() => {
    if (pathname !== "/admin/login" && !isLoading && isError) {
      navigate({ to: "/admin/login", replace: true });
    }
  }, [pathname, isLoading, isError, navigate]);

  // Login page: render without chrome
  if (pathname === "/admin/login") return <Outlet />;
  if (!admin) return null;

  const themeStyle = {
    "--primary": theme.primary,
    "--primary-foreground": theme.primaryForeground,
    "--accent": theme.accent,
    "--cream": theme.background,
    "--ring": theme.primary,
  } as React.CSSProperties;

  async function signOut() {
    try {
      await logout();
    } finally {
      queryClient.setQueryData<AdminUserOut | undefined>(["admin", "me"], undefined);
      queryClient.removeQueries({ queryKey: ["admin"] });
      navigate({ to: "/admin/login" });
    }
  }

  return (
    <div className="min-h-screen bg-cream flex flex-col" style={themeStyle}>
      <OperationalBanner />
      <div className="flex flex-1 min-h-0">
        {/* Sidebar */}
        <aside
          className={`${open ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0 fixed lg:static inset-y-0 left-0 z-40 w-64 bg-primary text-primary-foreground flex flex-col transition-transform`}
        >
          <div className="h-16 px-5 flex items-center justify-between border-b border-white/10">
            <Link to="/admin" className="font-display text-lg tracking-wide">
              Terrific · Admin
            </Link>
            <button className="lg:hidden" onClick={() => setOpen(false)}>
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="flex-1 overflow-y-auto py-3">
            {NAV.map((item) => {
              const active =
                item.to === "/admin" ? pathname === "/admin" : pathname.startsWith(item.to);
              const Icon = item.icon;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setOpen(false)}
                  className={`flex items-center gap-3 px-5 py-2.5 text-sm transition-colors ${active ? "bg-white/10 text-white border-l-2" : "text-primary-foreground/70 hover:bg-white/5 hover:text-white border-l-2 border-transparent"}`}
                  style={active ? { borderLeftColor: theme.sidebarActive } : undefined}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="p-4 border-t border-white/10 text-xs text-primary-foreground/70">
            <div className="mb-2">
              <div className="text-white font-medium">{admin.email}</div>
              <div className="capitalize">{admin.role.replace(/_/g, " ").toLowerCase()}</div>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/"
                className="flex-1 flex items-center justify-center gap-1 rounded bg-white/10 hover:bg-white/20 py-1.5"
              >
                <Home className="h-3 w-3" /> Store
              </Link>
              <button
                onClick={signOut}
                className="flex-1 flex items-center justify-center gap-1 rounded bg-white/10 hover:bg-white/20 py-1.5"
              >
                <LogOut className="h-3 w-3" /> Sign out
              </button>
            </div>
          </div>
        </aside>

        {/* Main */}
        <div className="flex-1 flex flex-col min-w-0">
          <header className="h-16 bg-white border-b flex items-center justify-between px-4 lg:px-8 sticky top-0 z-30">
            <div className="flex items-center gap-3">
              <button className="lg:hidden" onClick={() => setOpen(true)}>
                <Menu className="h-5 w-5" />
              </button>
              <h1 className="font-display text-lg text-stone-800">
                {NAV.find((n) =>
                  n.to === "/admin" ? pathname === "/admin" : pathname.startsWith(n.to),
                )?.label ?? "Admin"}
              </h1>
            </div>
            <div className="relative">
              <button
                onClick={() => setNotifOpen((v) => !v)}
                className="relative p-2 rounded-full hover:bg-stone-100"
              >
                <Bell className="h-5 w-5 text-stone-700" />
                {unread > 0 && (
                  <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-500" />
                )}
              </button>
              {notifOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-white border rounded-lg shadow-lg overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b">
                    <span className="font-medium text-sm">Notifications</span>
                    <button
                      onClick={() => notificationStore.markAllRead()}
                      className="text-xs text-stone-500 hover:text-stone-800"
                    >
                      Mark all read
                    </button>
                  </div>
                  <div className="max-h-80 overflow-y-auto">
                    {notifications.length === 0 && (
                      <div className="px-4 py-6 text-sm text-stone-500 text-center">
                        No notifications
                      </div>
                    )}
                    {notifications.map((n) => (
                      <button
                        key={n.id}
                        onClick={() => notificationStore.markRead(n.id)}
                        className={`w-full text-left px-4 py-3 border-b last:border-b-0 hover:bg-stone-50 ${!n.read ? "bg-amber-50/50" : ""}`}
                      >
                        <div className="text-sm font-medium text-stone-800">{n.title}</div>
                        <div className="text-xs text-stone-600 mt-0.5">{n.body}</div>
                        <div className="text-[10px] text-stone-400 mt-1">
                          {new Date(n.at).toLocaleString()}
                        </div>
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
    </div>
  );
}
