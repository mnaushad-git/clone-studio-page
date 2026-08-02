# Project Overview — Terrific Bites

_Audit date: 2026-07-27. This document reflects the state of the `baseline-terrific-bites-storefront-and-admin-ui` branch as inspected — no code was changed to produce this audit._

## What this repository is

A single TanStack Start application that contains **two UIs in one codebase**:

1. **Customer Storefront** — an artisan bakery e-commerce site ("Terrific Bites", Riyadh/Saudi-Arabia themed) with browsing, cart, checkout, account, order tracking, gift-recipient flows, and bilingual (English/Arabic, RTL) support.
2. **Admin Portal** — a `/admin/*` section for managing products, orders, promotions, delivery, staff, loyalty, content/theme, and analytics.

Both were generated and are actively maintained through **Lovable** (lovable.dev), a prompt-driven app builder that commits directly to this repo (see `AGENTS.md`, `.lovable/project.json`, `README.md`). Recent commit history (`Add full Arabic (RTL) translation`, `Clarified gift recipient rules`, `Added address picker modal`, `Enforced admin login on load`) confirms this is a live, evolving Lovable project, not a frozen scaffold.

**The single most important architectural fact:** there is no backend. Every "database" in this app is a hand-rolled, `localStorage`-backed store living entirely in the browser. Supabase is installed and wired for future use but currently has **zero tables** and is not read from or written to anywhere in the route/component code. Treat this whole app as a fully-clickable, data-realistic **prototype/demo**, not a system with persistence, multi-user support, or real security.

## Tech stack

| Layer | Technology | Version (from `package.json`) |
| --- | --- | --- |
| Framework | TanStack Start (file-based routing, SSR-capable) | `@tanstack/react-start@^1.168.26` |
| Router | TanStack Router | `@tanstack/react-router@^1.170.16` |
| UI library | React | `^19.2.0` |
| Language | TypeScript | `^5.8.3` (strict mode on) |
| Styling | Tailwind CSS v4 (CSS-first config, no `tailwind.config.js`) | `^4.2.1` |
| Component system | shadcn/ui ("new-york" style) on Radix UI primitives | see `components.json` |
| Data fetching plumbing | TanStack Query (`QueryClientProvider` wired in root, but not actually used for any queries found in this audit) | `@tanstack/react-query@^5.101.1` |
| Forms | react-hook-form + Zod resolvers | `^7.71.2` / `^3.24.2` |
| Backend-as-a-service (scaffolded, unused) | Supabase JS client | `@supabase/supabase-js@^2.110.8` |
| Build tool | Vite (via `@lovable.dev/vite-tanstack-config`) | `vite@^8.0.16` |
| Server runtime target | Nitro (Cloudflare Workers by default) | `nitro@3.0.260603-beta` |
| Package manager | Bun (`bun.lock`, `bunfig.toml` present) — npm also usable | — |
| PDF generation | jsPDF (client-side invoice generation) | `^4.2.1` |
| Charts | Recharts (used in `ui/chart.tsx`, admin analytics) | `^2.15.4` |
| Icons | lucide-react | `^0.575.0` |
| Linting/formatting | ESLint 9 (flat config) + Prettier | — |

Notably **absent**: no Next.js/Remix, no Redux/Zustand/Jotai (state is custom `useSyncExternalStore`), no CSS-in-JS, no test framework (no Jest/Vitest/Playwright config found), no CI config files found at the repo root.

## How the app is structured at a glance

- **Routing**: TanStack Start file-based routing under `src/routes/`. Flat dot-notation filenames (`admin.products.tsx` → `/admin/products`) rather than nested folders. `src/routeTree.gen.ts` is auto-generated — never hand-edit it.
- **Customer-facing state**: `src/lib/store.ts` — cart, orders, addresses, user/auth, wishlist, reviews, loyalty, location, gift-recipient confirmation tokens. Persisted to `localStorage["tb.state.v1"]`.
- **Admin/config state**: `src/lib/admin-store.ts` — staff, promo codes, delivery zones/slots, banners, categories, payment methods, loyalty config, site settings, per-product overrides, homepage section order, notifications, admin theme, mock admin session. Persisted to `localStorage["tb.admin.v1"]`.
- **Product catalog**: `src/lib/products.ts` — a static, hardcoded TypeScript array (28 products across 6 categories). Not editable at runtime except via admin "overrides" layered on top in `admin-store.ts`.
- **i18n**: `src/lib/i18n.ts` + `src/lib/i18n-dict/*.ts` — hand-rolled English/Arabic dictionary with RTL `dir` attribute switching. Not using a library like `i18next`.
- **Supabase**: `src/integrations/supabase/*` — client, server client (service role), auth middleware, and generated `Database` types are all present and structurally correct, but the `Database` type has no tables and no route or component in the app imports `supabase` for actual data. It is Lovable Cloud boilerplate, ready to be filled in, not currently load-bearing.
- **Component chrome**: `SiteHeader`/`SiteFooter`/`MegaMenu`/`CartDrawer` are composed **per-route**, not in the root layout (`__root.tsx` only renders `<Outlet />` + a maintenance banner + toaster). See [frontend-architecture.md](./frontend-architecture.md).

## Who this project is for / demo context

Currency is SAR (Saudi Riyal), delivery areas are Riyadh districts (`RIYADH_AREAS` in `store.ts`), and `location.ts` models 8 cities across 5 GCC/MENA countries (Saudi Arabia, UAE, Kuwait, Qatar, Egypt) — though only Riyadh is currently wired into the UI (see [gap-analysis.md](./gap-analysis.md) for the header's hardcoded "Riyadh" bug). This strongly suggests the target market is Gulf/MENA online bakery/gifting commerce.

## Related documents

- [folder-structure.md](./folder-structure.md) — annotated directory tree
- [routes.md](./routes.md) — every route, its data source, and completeness classification
- [mock-data.md](./mock-data.md) — every localStorage store, static data file, and what's actually persisted vs. fabricated
- [components.md](./components.md) — shared component inventory and hierarchy
- [frontend-architecture.md](./frontend-architecture.md) — state management, auth, SSR, i18n, error handling
- [gap-analysis.md](./gap-analysis.md) — per-page functional gaps, security issues, technical debt
- [roadmap.md](./roadmap.md) — proposed sequence for turning this into a production system, plus strengths/weaknesses/risks/open questions
