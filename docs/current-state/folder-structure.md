# Folder Structure

_Annotated tree of everything relevant to the application. `node_modules/`, `.git/`, `.tanstack/` (build cache) are omitted._

```
Terrific_Bites/
├── .env                          # Supabase URL + publishable key — committed to git (not in .gitignore!)
├── .gitignore
├── .lovable/
│   └── project.json              # Lovable project/template metadata (template: tanstack_start_ts_current)
├── .prettierignore / .prettierrc
├── AGENTS.md                     # Warning banner: repo is synced with Lovable, don't rewrite pushed history
├── README.md                     # Default Lovable README (generic, not project-specific)
├── bun.lock / bunfig.toml        # Bun is the primary package manager
├── components.json               # shadcn/ui config: style="new-york", baseColor="slate", alias @/components etc.
├── eslint.config.js               # Flat ESLint config (v9), React hooks + refresh + prettier plugins
├── package.json                  # name: "tanstack_start_ts" (generic template name, never renamed)
├── public/
│   └── favicon.ico                # Only static public asset
├── src/
│   ├── assets/                    # ~45 static images (jpg/png) imported directly into TS/TSX — product photos,
│   │                               # hero banners, gift box art, about-page imagery. One .asset.json sidecar
│   │                               # (logo-footer.png.asset.json) — Lovable asset-tracking metadata.
│   ├── components/
│   │   ├── admin/
│   │   │   └── ui.tsx             # Shared admin design-system primitives (Card, Stat, Field, Modal, Badge, etc.)
│   │   ├── ui/                    # Full shadcn/ui primitive library (~40 files: button, dialog, sheet, sidebar,
│   │   │                           # calendar, chart, carousel, form, command, etc.) — generated, not hand-authored
│   │   ├── CartDrawer.tsx         # Slide-out cart panel (mounted inside SiteHeader)
│   │   ├── DeliveryCountdown.tsx  # Same-day/next-day delivery countdown chip/banner
│   │   ├── MegaMenu.tsx           # Full-height nav drawer (mounted inside SiteHeader)
│   │   ├── OrderStatusTimeline.tsx# Processing → Paid → Delivered step visualization
│   │   ├── ProductCard.tsx        # Product tile (grid item) — cart/wishlist actions
│   │   ├── ProductReviews.tsx     # Review list + submission form (photo upload via base64)
│   │   ├── ShopGrid.tsx           # Reusable shop/category page template (filters, sort, grid) — used by 9 routes
│   │   ├── SiteFooter.tsx         # Standard footer (per-route, not global)
│   │   └── SiteHeader.tsx         # Standard header (per-route, not global) — hosts CartDrawer + MegaMenu
│   ├── hooks/
│   │   └── use-mobile.tsx         # useIsMobile() — standard shadcn-generated hook, viewport <768px
│   ├── integrations/
│   │   └── supabase/
│   │       ├── auth-attacher.ts   # Client middleware: attaches Supabase bearer token to server-fn calls
│   │       ├── auth-middleware.ts # Server middleware: validates Bearer JWT via supabase.auth.getClaims
│   │       ├── client.server.ts   # Service-role admin client (bypasses RLS) — server-only
│   │       ├── client.ts          # Browser/publishable-key client
│   │       └── types.ts           # Generated Database types — currently ZERO tables defined
│   ├── lib/
│   │   ├── i18n-dict/             # Per-feature en/ar string dictionaries (about, account, cart, checkout,
│   │   │                           # common, corporate, customizeDelivery, home, moments, product, shop)
│   │   ├── admin-store.ts         # Admin/config localStorage store (localStorage["tb.admin.v1"])
│   │   ├── error-capture.ts       # Global window error/unhandledrejection capture (for SSR crash recovery)
│   │   ├── error-page.ts          # Static HTML string for the "This page didn't load" 500 fallback
│   │   ├── i18n.ts                # useT()/useLang()/setLang() — dictionary merge + RTL dir switching
│   │   ├── location.ts            # CITIES list (8 cities/5 countries), delivery-cutoff-hour logic
│   │   ├── lovable-error-reporting.ts # Forwards React error-boundary errors to Lovable's editor telemetry
│   │   ├── products.ts            # Static product catalog (28 products) + category/occasion/recipient helpers
│   │   ├── store.ts               # Customer-facing localStorage store (localStorage["tb.state.v1"])
│   │   └── utils.ts               # cn() — clsx + tailwind-merge helper
│   ├── routes/                    # File-based routes — see routes.md for full per-file breakdown
│   │   ├── README.md              # TanStack Start file-routing conventions cheat sheet
│   │   ├── __root.tsx             # App shell: QueryClientProvider, MaintenanceBanner, <Outlet/>, Toaster
│   │   ├── admin.tsx              # /admin layout: sidebar, session guard, notifications, theme vars
│   │   ├── admin.*.tsx            # 14 admin subpages (analytics, categories, content, customers, delivery,
│   │   │                           # index, login, loyalty, orders, products, promotions, reviews, settings,
│   │   │                           # staff, theme)
│   │   ├── index.tsx              # Homepage (/) — hero, featured rails, gifts, divine treats, catering CTA
│   │   ├── (marketing pages)      # about, corporate, moments.index, moments.$slug, recipients.index,
│   │   │                           # recipients.$slug
│   │   ├── (shop pages)           # shop, cakes, chocolates, cupcakes, donuts, extras, gifts, product.$id
│   │   ├── (account/auth pages)   # login, signup, forgot-password, account, wishlist, confirm-address.$token
│   │   └── (checkout/order pages) # customize, delivery, payment, success, track.$id
│   ├── routeTree.gen.ts           # AUTO-GENERATED — do not hand-edit
│   ├── router.tsx                 # createRouter() factory (QueryClient context, scroll restoration)
│   ├── server.ts                  # Cloudflare-style fetch handler wrapper + SSR crash normalization
│   ├── start.ts                   # createStart() — registers global function/request middleware
│   └── styles.css                 # Tailwind v4 CSS-first theme (OKLCH color tokens, custom fonts)
├── supabase/
│   └── config.toml                # Just `project_id` — no migrations/, no functions/, no seed data
├── tsconfig.json                  # Strict TS, @/* path alias → src/*
└── vite.config.ts                 # Thin wrapper around @lovable.dev/vite-tanstack-config
```

## Notable structural observations

- **No `src/pages/`, no `app/` directory** — correctly follows TanStack Start's file-based routing convention (the repo's own `src/routes/README.md` explicitly warns against Next.js/Remix-style folders).
- **No test directory** — no `__tests__/`, `*.test.ts(x)`, `*.spec.ts(x)` files found anywhere in `src/`.
- **No CI/CD config** — no `.github/workflows/`, no `Dockerfile`, no deployment scripts beyond the Nitro/Cloudflare defaults baked into `@lovable.dev/vite-tanstack-config`.
- **`supabase/` directory is a stub** — only `config.toml` with a project ID; no `migrations/`, `functions/`, or `seed.sql`. Confirms Supabase is provisioned but not yet used as a real datastore.
- **`.env` is tracked by git** (not listed in `.gitignore`). It currently only contains a publishable/anon key and project URL (not a service-role secret), which is the intended public-facing key type for Supabase — but it's still worth moving to an untracked `.env.local` pattern before adding any secret values, since the service-role key referenced in `client.server.ts` (`SUPABASE_SERVICE_ROLE_KEY`) is not present yet and must never be committed the same way.
- **`package.json`'s `name` field is still the generic `"tanstack_start_ts"`** — never renamed to reflect the actual product, a small housekeeping item.
