# Routes — Full Inventory & Completeness Classification

All routes live in `src/routes/` (TanStack Start file-based routing; dot-notation = nested path, `$param` = dynamic segment). Classification legend:

- **UI Complete** — static/presentational, no backend ever needed (or genuinely done for its scope)
- **Mock Data** — works end-to-end but against hardcoded/fake data; would need a real backend to be trustworthy
- **Partially Functional** — some interactions are stubbed, disabled, or silently discarded
- **Fully Functional** — real working logic against the local store (cart math, CRUD, filters) — "real" within the constraints of local-only persistence
- **Needs Backend Integration** — currently a no-op or simulated fake without a real API (payment, email, OTP)

## Storefront — Marketing / Info Pages

| Route | File | Classification | Notes |
|---|---|---|---|
| `/` | `index.tsx` | **Partially Functional** | Hero, featured rails (from static `products.ts` `featured.*`, not admin overrides), gifts, "divine treats" carousel, catering CTA. Hero and "divine treats" prev/next arrow buttons render but have **no onClick handlers — dead buttons**. Does **not** read admin `banners` or `homepageSections` at all — the entire homepage layout is hardcoded, making `/admin/content` fully disconnected from what customers see (see [gap-analysis.md](./gap-analysis.md)). |
| `/about` | `about.tsx` | UI Complete | Static story/vision/testimonial content, i18n strings, static images. No data dependencies. |
| `/corporate` | `corporate.tsx` | Needs Backend Integration | Bulk-gifting lead form; "submits" via local `useState` only — `toast.success` fires but nothing is sent to an email/CRM/API. |
| `/moments` | `moments.index.tsx` | UI Complete | Occasion gallery (Birthday, Anniversary, Wedding, Graduation, Congratulations, Thank You) from static `OCCASIONS`. |
| `/moments/$slug` | `moments.$slug.tsx` | UI Complete | Occasion hero + `ShopGrid` locked to that occasion. |
| `/recipients` | `recipients.index.tsx` | UI Complete | "Shop by who it's for" gallery (For Him/Her/Kids/Family). |
| `/recipients/$slug` | `recipients.$slug.tsx` | UI Complete | Recipient-specific `ShopGrid`. |

## Storefront — Shop / Product Pages

| Route | File | Classification | Notes |
|---|---|---|---|
| `/shop` | `shop.tsx` | Fully Functional | All-products grid via `<ShopGrid initialCategory="all">` — client-side filter/sort/search over the static catalog. |
| `/cakes`, `/chocolates`, `/cupcakes`, `/donuts`, `/extras`, `/gifts` | `{cakes,chocolates,cupcakes,donuts,extras,gifts}.tsx` | Fully Functional | Thin wrappers around `ShopGrid` with `lockCategory`. |
| `/product/$id` | `product.$id.tsx` | Fully Functional | PDP: gallery, size/flavor selectors, qty, add-to-cart/buy-now, wishlist toggle, tabs, reviews, related + recently-viewed rails. Correctly merges static `products.ts` with **admin-store `productOverrides`** (price/stock/visibility/name/description/image/sizes/flavors/inscription). Real writes to `cart`, `wishlist`, `recentlyViewed`. "Points earned" preview is cosmetic display math, not tied to actual accrual elsewhere. |
| `/wishlist` | `wishlist.tsx` | Fully Functional | Reads `wishlist` ids + static catalog lookup; `wishlist.clear()`. |

## Storefront — Account / Auth Pages

| Route | File | Classification | Notes |
|---|---|---|---|
| `/login` | `login.tsx` | **Needs Backend Integration (fake auth)** | Phone-OTP flow: any phone → toast "OTP sent (demo)" → **any 4 digits accepted**, auto-submits after 300ms. Email/password flow: **any non-empty email+password succeeds**. No credential verification anywhere. |
| `/signup` | `signup.tsx` | **Needs Backend Integration (fake auth)** | Real Zod validation (name/email/phone/area/address/password ≥8/confirm match), but on success only calls `auth.signIn()` — **password is validated then discarded**, never stored or checked again. |
| `/forgot-password` | `forgot-password.tsx` | Needs Backend Integration | Real email Zod validation; "send" is a 700ms `setTimeout` fake; no email ever sent. |
| `/account` | `account.tsx` | Fully Functional (within local-store scope) | Profile, address CRUD, order history (with a self-service "Mark as Paid/Delivered" button calling `orders.advance()`), wallet/loyalty. **"Favorites", "Invoices", and "Occasions" tabs are inert empty-state placeholders** with no real content, despite being reachable from the sidebar. |
| `/confirm-address/$token` | `confirm-address.$token.tsx` | Fully Functional (local-store based) | Gift-recipient flow; token is a client-generated local-store key, not a cryptographically issued/emailed link — only "works" within the same browser. |

## Storefront — Checkout / Order Pages

| Route | File | Classification | Notes |
|---|---|---|---|
| `/customize` | `customize.tsx` | **Partially Functional** | Cart math and promo application are real. **The entire "Gift Card & Message" feature (card design, to/from/message/link) is captured in local component state and never attached to the cart or order** — it's silently discarded before checkout completes. |
| `/delivery` | `delivery.tsx` | Fully Functional | Real address CRUD, real slot computation reading admin-configured `slots` (via `getAdminState()`), saves to store before navigating on. |
| `/payment` | `payment.tsx` | **Needs Backend Integration (fake payment)** | Zod-validated card fields (Luhn-length, expiry, CVC) look real but no gateway is called — `setTimeout(1200ms)` simulated delay, then `orders.place()` directly. Card number/CVC validated then discarded (only last 4 digits kept for display). No charge occurs anywhere. |
| `/success` | `success.tsx` | Fully Functional (mock flow) | Order confirmation, status timeline, client-generated PDF invoice (`jsPDF`), tracking link. **Auto-advances order status Processing→Paid after 600ms** via `setTimeout` (simulated backend confirmation) plus a manual override button. |
| `/track/$id` | `track.$id.tsx` | Fully Functional (local-store based) | Looks up order by `trackingToken`; courier name/phone is static mock data seeded at order-creation time, not a live GPS/courier integration. |

## Admin Portal (`/admin/*`)

All admin pages inherit routing/session handling from `admin.tsx` (see [frontend-architecture.md](./frontend-architecture.md) for the full auth-guard analysis — **summary: client-side only, trivially bypassable via localStorage, no RBAC**).

| Route | File | Classification | Notes |
|---|---|---|---|
| `/admin/login` | `admin.login.tsx` | Mock Data | Form **pre-filled** with working owner credentials (`owner@terrificbites.sa` / `admin123`) and prints them in a visible "Demo" hint — the login screen ships pre-armed for full owner access. |
| `/admin` | `admin.index.tsx` | Fully Functional (local data) | Dashboard KPIs computed live from real local `orders`/`reviews` (not fabricated), plus static catalog/staff counts. |
| `/admin/orders` | `admin.orders.tsx` | Fully Functional (local data) | Order list/search/filter, inline status change via `orders.setStatus()` — no transition validation, no audit trail. |
| `/admin/products` | `admin.products.tsx` | **Partially Functional** | Genuine CRUD-over-overrides pattern (consumed correctly by `product.$id.tsx`), but never mutates the base catalog; "stock" field has no relationship to any cart/checkout decrement logic — display-only. |
| `/admin/categories` | `admin.categories.tsx` | **Mock Data** | CRUD works and persists, but this `categories` list is a **separate source of truth** from `products.ts`'s hardcoded `Category` union — edits here don't verifiably affect the storefront's actual category taxonomy or `ShopGrid`'s filter sidebar. |
| `/admin/customers` | `admin.customers.tsx` | Mock Data (by architecture) | Code comment states it directly: only tracks the one locally-signed-in user + guest-by-address orders — no real multi-customer database is possible without a backend. |
| `/admin/delivery` | `admin.delivery.tsx` | Partially Functional | Slots (`slotStore`) are genuinely wired into checkout (`delivery.tsx` reads active slots). Zones (`zoneStore`) fee/ETA fields were not found consumed anywhere — likely display-only; actual delivery fee comes from `settings.defaultDeliveryFee`. |
| `/admin/content` | `admin.content.tsx` | **Mock Data** | CRUD for banners/homepage sections persists correctly, but **the homepage (`index.tsx`) does not read either value** — confirmed by direct inspection. This page currently has zero effect on the live storefront. |
| `/admin/reviews` | `admin.reviews.tsx` | Fully Functional (local data) | Real reviews array, real delete; no moderation workflow (no approve/reject/flag/reply). |
| `/admin/loyalty` | `admin.loyalty.tsx` | Fully Functional | Confirmed consumed by `store.ts`'s real points-redemption math at checkout. |
| `/admin/promotions` | `admin.promotions.tsx` | Fully Functional | Confirmed consumed by `promo.apply()` at checkout, including min-subtotal/usage-limit checks. **Usage counter (`used`) is never incremented on real redemption** — usage limits are effectively unenforced over repeat use. |
| `/admin/settings` | `admin.settings.tsx` | Partially Functional | `taxRate`/`minOrder` confirmed wired into real checkout math. `maintenanceMode`, `guestCheckout`, `languages`, `socials` enforcement not fully confirmed beyond `maintenanceMode`'s banner in `__root.tsx`. |
| `/admin/staff` | `admin.staff.tsx` | Fully Functional CRUD, **critical security gap** | Any signed-in role (including `kitchen`/`support`) can edit their own record's `role` to `"owner"` with zero server-side or role-based restriction — full self-service privilege escalation. See [gap-analysis.md](./gap-analysis.md). |
| `/admin/theme` | `admin.theme.tsx` | Fully Functional | Admin-panel-only cosmetic theming, correctly self-contained, lowest risk page in the section. |
| `/admin/analytics` | `admin.analytics.tsx` | Fully Functional (real computation, sparse data) | Every number is derived via real `reduce`/`Map` aggregation over local `orders` — nothing is `Math.random()`-fabricated. Charts will look sparse/empty without manually placing several test orders in the same browser. |

## Cross-cutting observations

- **No route in the entire app imports `@/integrations/supabase/*`.** Confirmed by direct inspection of every storefront and admin route file. Supabase is 100% unused at the application level today.
- **Dynamic (`$param`) routes:** `confirm-address.$token.tsx`, `moments.$slug.tsx`, `product.$id.tsx`, `recipients.$slug.tsx`, `track.$id.tsx`.
- **Simulated async (`setTimeout`-based fakes) present in:** `login.tsx` (OTP), `forgot-password.tsx` (reset email), `payment.tsx` (payment processing), `success.tsx` (auto status advance).
- See [gap-analysis.md](./gap-analysis.md) for the consolidated list of stubbed features, security gaps, and disconnected admin controls.
