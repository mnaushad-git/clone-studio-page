# Gap Analysis

Consolidated list of functional gaps, disconnected features, security issues, and technical debt found during the audit. Organized by severity/category, not by file. Nothing here has been fixed — this is a findings document only.

## 1. Security — Critical (fix before any real user, staff, or payment data touches this app)

| # | Finding | Where | Impact |
|---|---|---|---|
| 1.1 | Customer login accepts any email/phone + any password/OTP — zero credential verification | `src/routes/login.tsx`, `src/lib/store.ts` `auth.signIn` | Anyone can "sign in" as anyone; not a real auth system |
| 1.2 | Admin login password is a single hardcoded literal (`"admin123"`), and the login page **displays the working owner credentials in a visible "Demo" hint** with the form pre-filled | `admin.login.tsx`, `admin-store.ts` `adminAuth.signIn` | Full owner access to any visitor who loads `/admin/login` |
| 1.3 | Admin route guard is 100% client-side, reads `localStorage` directly, and the `beforeLoad` SSR check is a no-op (`if (typeof window === "undefined") return`) | `src/routes/admin.tsx` | Anyone can craft `localStorage["tb.admin.v1"].adminSession` in DevTools and access any `/admin/*` page with zero login |
| 1.4 | No role-based access control anywhere — every role (`owner/admin/manager/support/kitchen`) sees and can mutate every admin page and store | `admin.tsx` layout, all `admin.*.tsx` pages | A "kitchen" or "support" session has the same power as "owner" |
| 1.5 | Self-service privilege escalation: any signed-in admin session can edit its own staff record's `role` to `"owner"` with no server check | `admin.staff.tsx`, `staffStore.update` | Complete authorization bypass in two clicks |
| 1.6 | Payment form validates realistic card data (number, expiry, CVC) but performs no real transaction — gives a false impression of a working payment system | `payment.tsx` | Must be replaced with a real PCI-compliant flow (e.g. hosted fields/tokenization), not patched |

**Recommendation**: none of 1.1–1.5 are "bugs" in the traditional sense — they are exactly what you'd expect from a Lovable-generated demo with no backend. They must be treated as a hard blocker list before connecting this app to real customer or staff data, not incremental fixes.

## 2. Disconnected admin controls (admin panel accepts input that has no effect on the storefront)

| # | Admin page | What breaks |
|---|---|---|
| 2.1 | `/admin/content` (banners + homepage sections) | `index.tsx` (homepage) does not read `banners` or `homepageSections` at all — this entire admin page currently has **zero effect** on what customers see |
| 2.2 | `/admin/categories` | Separate source of truth from `products.ts`'s hardcoded `Category` union and from `ShopGrid`'s own hardcoded `CATEGORIES` filter list — editing/reordering/hiding a category here does not verifiably change the shop filter sidebar or product categorization |
| 2.3 | `/admin/delivery` → zones | `zoneStore` fee/ETA fields were not found consumed by checkout — actual delivery fee comes from `settings.defaultDeliveryFee`/`freeDeliveryThreshold` instead, so per-zone pricing looks configurable but isn't wired in |
| 2.4 | `/admin/products` → stock field | No cart/checkout logic decrements stock on order placement — stock is display-only, not enforced |
| 2.5 | `/admin/promotions` → usage limit | `promo.apply()` checks `used >= usageLimit`, but nothing increments `used` on a successful order — usage limits are effectively unenforced after the first check |
| 2.6 | Homepage "featured" rails | Always pull from static `products.ts` `featured.*` slices, ignoring admin `productOverrides.featured`/`.visible` flags — an admin marking a product as "not visible" or "featured" has no confirmed effect on the homepage |

## 3. Stubbed or discarded user-facing features

| # | Feature | Where | Detail |
|---|---|---|---|
| 3.1 | Gift card design + gift message composer | `customize.tsx` | Entire feature (card design, to/from/message/link) is local component state, never attached to the cart or the placed order — silently discarded |
| 3.2 | Corporate/bulk-gifting lead form | `corporate.tsx` | "Submits" instantly with no delay and no real send — no email/CRM/API call of any kind |
| 3.3 | Forgot-password flow | `forgot-password.tsx` | Real Zod email validation, but "send" is a 700ms fake delay; no email is ever sent |
| 3.4 | Account page: Favorites / Invoices / Occasions tabs | `account.tsx` | Reachable from the sidebar but render only generic empty-state placeholders — no functionality behind them |
| 3.5 | Homepage carousel arrows | `index.tsx` (hero + "divine treats" sections) | Prev/next buttons render but have no `onClick` handlers — decorative dead buttons |
| 3.6 | Footer "Company"/"Help" links | `SiteFooter.tsx` | All point to `href="#"` — dead links, though correctly translated text |
| 3.7 | Simulated backend behavior throughout checkout | `login.tsx` (OTP), `payment.tsx` (processing delay), `success.tsx` (auto status advance) | All `setTimeout`-based fakes standing in for what will eventually be real async operations — useful as a map of exactly where real API calls need to be inserted |

## 4. Data-consistency bugs

| # | Finding | Where |
|---|---|---|
| 4.1 | Header always displays "Riyadh"/🇸🇦 regardless of the actual selected `location` in the store | `SiteHeader.tsx` vs. `DeliveryCountdown.tsx` (which correctly reads `s.location`) — the app's own multi-city model (`location.ts`, 8 cities) has no working UI entry point to actually change city |
| 4.2 | `MegaMenu` mixes TanStack `<Link>` (SPA nav) and plain `<a href>` (full reload) for primary navigation | `MegaMenu.tsx` |
| 4.3 | `MegaMenu`'s slide-in is hardcoded to the left edge with physical CSS (`-translate-x-full`), ignoring `dir="rtl"` | `MegaMenu.tsx` |
| 4.4 | Locale-independent date formatting (`toLocaleDateString()` with no locale arg) doesn't follow the app's own language toggle | `OrderStatusTimeline.tsx`, `ProductReviews.tsx` |
| 4.5 | Seeded demo reviews are re-merged back into the store on every load, so "delete review" in `/admin/reviews` isn't durable across the 5 seeded ids | `store.ts` `load()` |
| 4.6 | Hardcoded `"SAR"` currency literal in `CartDrawer`/`ProductCard`, not city-currency-aware despite the data model supporting it | `CartDrawer.tsx`, `ProductCard.tsx` |

## 5. Technical debt (not bugs, but will slow down future work)

- **Two independent category taxonomies** (admin-configurable vs. static `products.ts` union vs. `ShopGrid`'s own hardcoded list) — needs unification before a real product/category backend is built.
- **No consistent i18n interpolation strategy** — manual `{{token}}` replace, string concatenation, and plain key lookups coexist across components.
- **Per-`ProductCard` `setInterval` timers** for delivery countdown — should be centralized (e.g., a single shared ticking context) before scaling the catalog.
- **Base64 photo storage directly in the localStorage-backed store** (`ProductReviews`) — a real scalability ceiling; must move to real file/object storage (e.g., Supabase Storage or S3) alongside any backend migration.
- **`noUnusedLocals`/`noUnusedParameters` disabled** in `tsconfig.json` — worth re-enabling once the codebase stabilizes, to catch dead code from future refactors.
- **No automated tests of any kind** (no Vitest/Jest/Playwright config) — every one of the fake/simulated behaviors documented here was found by manual reading, not caught by a test suite.
- **`package.json`'s `name` field** is still the generic scaffold name `"tanstack_start_ts"`.
- Lovable-specific error-reporting hooks (`lovable-error-reporting.ts`) are dead code outside the Lovable editor preview and should be revisited once hosting moves elsewhere.

## 6. Missing functionality (features implied by the data model but not built anywhere)

- **No UI to switch delivery city/country**, despite `location.ts` modeling 8 cities across 5 countries.
- **No "add new product" admin flow** — only editing overrides on the fixed 28-product catalog; there's no way to add a genuinely new SKU without a code change to `products.ts`.
- **No order-status transition validation** — admin can set any order to any status in any order, with no audit trail of who made the change.
- **No review moderation** beyond delete (no approve/reject/flag/reply workflow).
- **No real multi-customer data model** — `admin.customers.tsx`'s own code comment admits it only tracks the single locally-signed-in browser session plus guest orders by address; a real customer database requires a backend by definition.

## Summary

The UI is broad and largely complete-looking, but almost every page that appears to "do something real" is actually reading and writing the same two `localStorage` blobs (`tb.state.v1`, `tb.state.v1`'s sibling `tb.admin.v1`). A small number of admin-configurable values genuinely do flow through to the storefront (promo codes, delivery slots, tax rate, loyalty redeem rate, product overrides) — those are the pieces of the admin panel that are load-bearing today. Everything else (banners, homepage sections, categories, delivery zones, most of settings) is either disconnected or unconfirmed. See [roadmap.md](./roadmap.md) for a proposed sequence to close these gaps.
