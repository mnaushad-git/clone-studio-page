# Frontend Architecture

## Routing

TanStack Start file-based routing (`src/routes/`). `src/router.tsx` builds the router via `createRouter({ routeTree, context: { queryClient }, scrollRestoration: true, defaultPreloadStaleTime: 0 })`. Route tree is auto-generated into `src/routeTree.gen.ts` (never hand-edited).

- Static routes: plain filenames (`about.tsx` → `/about`).
- Dynamic routes: bare-`$` (`product.$id.tsx` → `/product/:id`, `moments.$slug.tsx`, `recipients.$slug.tsx`, `track.$id.tsx`, `confirm-address.$token.tsx`).
- Nested/admin routes: dot-notation flattening (`admin.products.tsx` → `/admin/products`) rather than folder nesting.
- Root layout `__root.tsx` defines `head()` (global `<meta>`/`<link>` tags — SEO/social preview tags are hardcoded per-app, not per-page, except `index.tsx` which overrides them with identical content), `notFoundComponent` (404), `errorComponent` (route-level error boundary that also forwards to `reportLovableError`), and `shellComponent` (the literal `<html>/<head>/<body>` wrapper, required for SSR).

## SSR / server architecture

This is not a plain SPA — it runs through TanStack Start's SSR pipeline targeting **Nitro with a Cloudflare Workers preset by default** (per `vite.config.ts`'s comment). Three files coordinate this:

- **`src/start.ts`** — `createStart()` registers global middleware: `functionMiddleware: [attachSupabaseAuth]` (attaches a bearer token to every server-function call, whether or not that function needs auth) and `requestMiddleware: [errorMiddleware]` (catches server-function throws that aren't already `statusCode`-bearing HTTP errors and replaces them with a generic rendered error page instead of letting a raw exception leak).
- **`src/server.ts`** — the actual fetch handler entrypoint (`server: { entry: "server" }` in `vite.config.ts`). Wraps the real TanStack `server-entry` handler and adds a specific workaround: h3 (Nitro's HTTP layer) sometimes swallows an in-handler throw into a generic `{"unhandled":true,"message":"HTTPError"}` JSON 500 response that bypasses normal try/catch — `normalizeCatastrophicSsrResponse()` detects that exact shape and substitutes the friendly static error page (`error-page.ts`) instead, recovering the real error from `error-capture.ts`'s out-of-band `window`/`globalThis` error listener for logging.
- **`src/lib/error-capture.ts` / `error-page.ts` / `lovable-error-reporting.ts`** — a three-part error-handling chain: capture (global listeners), render (static HTML string, no framework dependency, since this fires when the framework itself may have failed), and report (forwards React error-boundary catches to `window.__lovableEvents`/`window.__lovableReportRuntimeError`, which only exist inside the Lovable editor's preview iframe — meaningless in a real production deploy outside Lovable).

**Implication for a production migration**: this error-handling machinery is tightly coupled to Lovable's specific SSR quirks (h3/Nitro/Cloudflare) and its own editor telemetry hooks. It should be reviewed/simplified once the app moves to a standard hosting/observability setup (see [roadmap.md](./roadmap.md)) — some of it (the h3-swallowed-error workaround) may still be needed if staying on Nitro/Cloudflare, but the Lovable-specific reporting hook is dead weight outside the Lovable editor.

## State management

No Redux/Zustand/Jotai/Context-based global state. Both stores use the same hand-rolled pattern:

```ts
let state: State = load();                    // hydrate from localStorage (or `initial` on server/first load)
const listeners = new Set<() => void>();
function persist() { localStorage.setItem(KEY, JSON.stringify(state)); }
function emit() { persist(); listeners.forEach(l => l()); }
function subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); }
export function useStore<T>(selector: (s: State) => T): T {
  return useSyncExternalStore(subscribe, () => selector(state), () => selector(initial));
}
```

Mutations are plain exported objects grouped by domain (`cart.add()`, `orders.place()`, `addresses.update()`, etc.) that reassign the module-level `state` variable and call `emit()`. This is a legitimate, dependency-free pattern for a project this size, and correctly handles SSR (the third `useSyncExternalStore` argument returns `initial` server-side, since `isBrowser` gates all `localStorage` access). Two independent stores exist:

1. **`src/lib/store.ts`** (key `tb.state.v1`) — customer/session data.
2. **`src/lib/admin-store.ts`** (key `tb.admin.v1`) — site configuration/admin data.

They cross-reference each other one-directionally: `store.ts` calls `getAdminState()` (a non-reactive snapshot getter) to read admin-configured tax rate, delivery fee, promo codes, and loyalty redeem rate at calculation time — but `admin-store.ts` never imports from `store.ts` except where admin pages display customer-facing order/review data directly via `useStore`.

**TanStack Query is installed and wired** (`QueryClientProvider` in `__root.tsx`, `QueryClient` created in `router.tsx`) but no route or component in this audit was found calling `useQuery`/`useMutation` — it's present as scaffolding for future real API calls, not currently doing anything.

## Authentication — customer-facing

`auth` object in `store.ts`: `signIn(user)`, `signOut()`, `updateProfile(patch)`. All three simply write a `User` object (`{name?, email?, phone?, birthDate?}`) to the local store — **no password is ever stored, checked, or transmitted anywhere.** `login.tsx`'s phone-OTP path accepts any 4 digits; its email/password path accepts any non-empty pair. `signup.tsx` validates a password with Zod (≥8 chars, confirm-match) purely as client-side form UX, then discards it. This is **not authentication** in any real sense — it is a "remember a display name" mechanism. See [gap-analysis.md](./gap-analysis.md) for the security framing.

## Authentication — admin portal

`adminAuth` object in `admin-store.ts`: `signIn(email, password)` checks the email against the local `staff` array (must be `active: true`) and the password against the **literal hardcoded string `"admin123"`**. On success, writes `{ email, role }` straight into the same client-editable localStorage blob as `adminSession`. `admin.tsx` (the `/admin` layout) gates access with:

1. A route `beforeLoad` that reads `localStorage["tb.admin.v1"].adminSession` and redirects to `/admin/login` if absent — but this check is wrapped in `if (typeof window === "undefined") return`, meaning it **only ever runs client-side after hydration**, never during SSR.
2. A client `useEffect` in the `AdminLayout` component that re-checks the reactive `useAdmin` session and navigates away if missing, rendering `null` in the meantime.

Both layers read the same client-writable localStorage value with **no server round-trip, no signed session token, and no per-role authorization check on any individual admin page or store mutation**. Every admin page and every `*Store.update/add/remove` function is reachable by any role once `adminSession` exists — including a "kitchen" or "support" account editing their own `admin.staff.tsx` record to set `role: "owner"`. See [gap-analysis.md](./gap-analysis.md) for the full severity writeup — this is the highest-priority item before any real users touch the admin portal.

## Supabase — present but unwired

`src/integrations/supabase/` contains fully correct, idiomatic scaffolding:
- `client.ts` — browser client using the publishable key, with a `Proxy`-based lazy singleton and a custom `fetch` wrapper that strips a stale bearer-token header for the new opaque `sb_publishable_...` key format.
- `client.server.ts` — server-only service-role client (bypasses RLS), explicitly commented "never expose to client code."
- `auth-attacher.ts` — client middleware attaching the current Supabase session's bearer token to every TanStack Start server-function call (registered globally in `start.ts`).
- `auth-middleware.ts` — server middleware (`requireSupabaseAuth`) that validates an incoming Bearer JWT via `supabase.auth.getClaims()` and injects `{ supabase, userId, claims }` into the server-function context — this is the "real" auth pattern the app is clearly designed to grow into, but it is **not currently invoked by any route or server function**.
- `types.ts` — generated `Database` type with **zero tables/views/functions/enums defined** (`[_ in never]: never` everywhere) — confirms no Supabase schema has been created yet.
- `supabase/config.toml` (repo root) — just a `project_id`, no `migrations/`, no `functions/`.

**Conclusion: Supabase is provisioned (a real project ID and publishable key exist in `.env`) but has no schema and is not called from anywhere in the app.** This is the natural on-ramp for the future backend (see [roadmap.md](./roadmap.md)), not a currently-functioning integration.

## Internationalization (i18n) / RTL

Hand-rolled, not a library (no `i18next`/`react-intl`). `src/lib/i18n.ts`:
- `Lang = "en" | "ar"`, persisted to `localStorage["tb.lang"]`.
- `setLang()` also sets `document.documentElement`'s `lang`/`dir` attributes directly (`dir="rtl"` for Arabic) — this is what drives the app's RTL layout, combined with Tailwind logical-property classes (`ms-`/`me-`/`ps-`/`pe-`/`start-`/`end-`) used throughout most components.
- Dictionary is composed by merging ~11 per-feature dictionary modules (`src/lib/i18n-dict/*.ts`) into one `dict.en`/`dict.ar` object; `useT()` returns a typed lookup function (`TKey = keyof typeof dict.en` gives compile-time key safety).
- **Known inconsistencies** (see [components.md](./components.md)): a few components bypass `t()` entirely for some strings (`SiteHeader`'s `aria-label="Search"`), some hardcode English-only date formatting (`toLocaleDateString()` with no locale arg in `OrderStatusTimeline`/`ProductReviews`), and `MegaMenu`'s slide-in direction is hardcoded left-to-right regardless of `dir`.
- Interpolation has no single strategy — manual `{{token}}` string replace in one component, plain concatenation in others, no shared helper.

## Styling

Tailwind CSS v4, CSS-first configuration (no `tailwind.config.js` — theme tokens live directly in `src/styles.css` via `@theme inline` + OKLCH color values under `:root`/`.dark`). `tw-animate-css` supplies animation utility classes. `components.json` confirms shadcn/ui "new-york" style with `baseColor: slate`. Custom fonts loaded via Google Fonts `<link>` tags in `__root.tsx`'s `head()` (Cinzel for display, Dancing Script for script accents, Inter for body/sans).

## Performance concerns (structural, not measured)

- **Product catalog and all filtering is fully client-side and in-memory** (`ShopGrid`'s `useMemo` over the entire static array on every keystroke) — fine at 28 products, will not scale to a real catalog without pagination/server-side filtering.
- **Per-card timers**: every `ProductCard` mounts its own `DeliveryCountdown` with an independent `setInterval(60s)` — a grid of 20+ products means 20+ concurrent intervals doing near-identical work.
- **Base64 photo storage in `localStorage`** (`ProductReviews`) — real risk of hitting the ~5-10MB browser storage quota and corrupting the entire `tb.state.v1` blob (cart, orders, everything) if enough reviews with photos accumulate.
- **`defaultPreloadStaleTime: 0`** in `router.tsx` disables TanStack Router's preload caching — every link hover/preload re-runs loaders with no staleness window; likely fine today since there are no real network loaders, but worth revisiting once real data fetching (Supabase/API) is introduced.
- No image optimization pipeline (`loading="lazy"` is used, but images are plain static JPGs/PNGs bundled directly, no responsive `srcset`/CDN transforms).
- No code-splitting strategy beyond whatever Vite/TanStack Router does automatically per-route.

## Security concerns (structural summary — see gap-analysis.md for full detail)

1. Customer auth accepts any credentials (no verification).
2. Admin auth uses a single hardcoded password, visible in the login page's UI copy, with no RBAC enforcement anywhere.
3. All "sessions" (customer and admin) live in plain, unencrypted, user-editable `localStorage` — trivially forged by editing DevTools storage.
4. Payment form collects and validates real-looking card data (number/expiry/CVC) client-side with no actual transmission, but a real integration must replace this with a proper PCI-compliant tokenization flow (e.g., Stripe Elements) rather than raw card fields, however briefly held.
5. `.env` (containing the Supabase URL + publishable key) is committed to git — acceptable for a publishable/anon key by Supabase's own design, but the repo's `.gitignore` should be updated before a `SUPABASE_SERVICE_ROLE_KEY` or any other secret is ever added to a tracked env file.

## Build tooling

- **Vite 8** via `@lovable.dev/vite-tanstack-config`, which itself bundles: TanStack devtools (dev-only), `tanstackStart()`, `viteReact()`, `tailwindcss()`, `vite-tsconfig-paths`, Nitro (Cloudflare preset by default), env-var injection, React/TanStack dedupe, and Lovable's own error-logger/sandbox-detection plugins. The project's own `vite.config.ts` is intentionally thin — a comment explicitly warns against re-adding any of these plugins manually.
- **TypeScript** strict mode, `@/*` → `src/*` path alias, `noUnusedLocals`/`noUnusedParameters` both **disabled** (worth tightening for a production codebase).
- **ESLint 9** flat config with `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `eslint-config-prettier`/`eslint-plugin-prettier` (Prettier violations surface as lint errors rather than a separate format-check step).
- **Bun** is the primary package manager (`bun.lock`, `bunfig.toml`), though npm scripts in `package.json` work identically (`dev`, `build`, `build:dev`, `preview`, `lint`, `format`).
- **No test runner configured** — no Vitest/Jest/Playwright dependency or config file found anywhere in the repo.
