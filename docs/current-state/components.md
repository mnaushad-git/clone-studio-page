# Component Inventory & Hierarchy

## Design-system layer: `src/components/ui/*`

The full shadcn/ui ("new-york" style, Radix-based) primitive set — ~40 files (accordion, alert-dialog, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input, input-otp, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toggle, toggle-group, tooltip). These are generated, largely unmodified shadcn output — treat as vendor code, not application logic. `components.json` confirms the shadcn config (`style: new-york`, `baseColor: slate`, `iconLibrary: lucide`, `rtl: false` — note this RTL flag is the shadcn generator setting, not the app's actual runtime RTL support, which is handled separately by `i18n.ts`).

`src/components/admin/ui.tsx` is a small parallel design-system file specific to the admin portal: `Card`, `Stat`, `Field`, `Input`, `Textarea`, `Select`, `Button` (primary/ghost/danger/outline), `Toggle`, `Badge` (default/success/warn/danger/info), `EmptyState`, `Modal`. Pure presentational, no store coupling, no stubs/TODOs found.

## Business components: `src/components/*.tsx`

| Component | Used by | Reads | Mutates | Notable |
|---|---|---|---|---|
| `SiteHeader` | ~15 individual routes (imported directly, not global) | `selectCartCount`, `wishlist.length`, `user`, `useAdmin(settings.brandName)`, `useLang()` | `setLang()` | Hosts `CartDrawer` + `MegaMenu` internally with local open-state — every page gets its own instance. **Location chip hardcoded to "Riyadh"/🇸🇦, ignores `s.location`** entirely — a real data-consistency bug against the app's own multi-city model. `aria-label="Search"`/`"Wishlist"` are hardcoded English, not run through `t()`. |
| `SiteFooter` | Same routes as `SiteHeader`, plus rendered by `ShopGrid` | `useAdmin(settings, categories)` | — | "Company"/"Help" columns and payment badges (`VISA/AMEX/PayPal/GPay`) are hardcoded placeholder content with dead `href="#"` links. |
| `MegaMenu` | Mounted inside `SiteHeader` | `useAdmin(categories)` | — | Hardcoded `CAT_IMG` image map (extras→gifts image reuse gap). Mixes TanStack `<Link>` (static tiles) with plain `<a href>` (dynamic category rows) — the latter forces full page reloads. Hardcoded left-side slide-in (`-translate-x-full`) ignores RTL — will still open from the left in Arabic mode. |
| `CartDrawer` | Mounted inside `SiteHeader` | `cart`, `promo`, `loyaltyPoints`, `redeemedPoints`, `user`; `useAdmin(settings, loyalty)` | `cart.add/setQty/remove`, `promo.apply/clear`, `loyalty.clearRedeem/setRedeemPoints` | Guest vs. signed-in views diverge (guests see reduced totals + sign-in prompt). Hardcoded `"SAR"` currency string (not city-currency-aware). Duplicates tax-calculation logic for the guest path instead of reusing `selectTax`. No open/close transition (`null` when closed, no animation). |
| `ProductCard` | `ShopGrid` grid, homepage rails | `selectIsWishlisted`, `selectAverageRating` | `cart.add`, `wishlist.toggle` | Embeds its own `DeliveryCountdown` — N cards on a grid = N independent 60s timers. Toast messages built by string concatenation (`${name} ${t(...)}`), not templated — fragile for Arabic word order. |
| `ShopGrid` | 9 route files (`shop`, category pages, `moments.$slug`, `recipients.$slug`) | Static `products.ts`, `OCCASIONS`, `RECIPIENTS` | — (delegates to `ProductCard` for cart/wishlist actions) | The primary reusable "page template" — all filtering (search, price bucket, occasion, recipient, sort) is client-side `useMemo` over the full catalog. Its own hardcoded `CATEGORIES` constant is a **second, disconnected source of truth** vs. `MegaMenu`'s admin-driven categories — admin category edits don't reach this filter sidebar. Composes `SiteHeader` (optional via `hideHeader`) + `SiteFooter` unconditionally. |
| `DeliveryCountdown` | `ProductCard` (chip variant); designed for a `banner` variant too | `useStore(s => s.location)` | — | Self-ticking every 60s. Correctly reads the store's `location` (unlike `SiteHeader`). Ignores `location.ts`'s pre-built English `label`/`short` strings in favor of its own `t()`-based reconstruction — meaning those fields are effectively dead code today. |
| `ProductReviews` | Product detail page (`product.$id.tsx`) | `reviews`, `selectAverageRating`, `user`, `selectHasPurchased` | `reviews.add()` | Photo upload via `FileReader.readAsDataURL` → **base64 images stored directly in localStorage** (capped 3 photos / 800KB each) — a genuine scalability risk since localStorage has ~5-10MB browser limits. Star-rendering logic (`[1,2,3,4,5].map`) duplicated 3× in the same file. |
| `OrderStatusTimeline` | Order tracking/confirmation/history views | Pure props (`order: Order`, `compact?: boolean`) — no store hooks | — | Purely presentational. `formatStamp` uses `toLocaleDateString(undefined, ...)` — ignores the app's own `useLang()` toggle, so Arabic mode still shows browser-locale-formatted dates. No RTL-aware step ordering (`flex-row` assumes LTR left-to-right progression). |

## Hooks

`src/hooks/use-mobile.tsx` — `useIsMobile()`, a standard shadcn-generated `matchMedia` hook (768px breakpoint). **Not imported by any of the 9 business components above** — they rely on Tailwind responsive classes instead (`hidden md:flex`, etc.), so this hook currently has no confirmed consumer in the storefront (may be used inside `ui/sidebar.tsx` or admin pages not covered by this pass).

## Component hierarchy — the key architectural fact

**`src/routes/__root.tsx` renders only `<QueryClientProvider><MaintenanceBanner /><Outlet /><Toaster /></QueryClientProvider>`.** There is no `SiteHeader`/`SiteFooter`/`MegaMenu`/`CartDrawer` in the root shell. Instead:

- `SiteHeader` and `SiteFooter` are imported and rendered **individually inside at least 15 separate route files** (`index.tsx`, `about.tsx`, `account.tsx`, `customize.tsx`, `product.$id.tsx`, `payment.tsx`, `wishlist.tsx`, `track.$id.tsx`, `success.tsx`, `corporate.tsx`, `confirm-address.$token.tsx`, `moments.index.tsx`, `recipients.index.tsx`, `delivery.tsx`), plus internally by `ShopGrid.tsx` for the 9 shop/category routes.
- This means **every route is individually responsible for remembering to render the standard chrome** — nothing in the framework enforces it. A new page can trivially ship without a header or footer.
- `CartDrawer` and `MegaMenu` are mounted **inside `SiteHeader`**, so every page that renders `SiteHeader` gets its own independent instance of both drawers with page-local open/close state — there is no single app-level cart-drawer singleton.
- Admin routes (`admin.*.tsx`) do not use `SiteHeader`/`SiteFooter`/`MegaMenu`/`CartDrawer` at all — they have their own shell in `admin.tsx` (sidebar nav + header), entirely separate from the storefront chrome.

**Practical implication (informational — no action taken as part of this audit):** hoisting `SiteHeader`/`SiteFooter` into `__root.tsx` (with an opt-out for admin/auth pages) would remove the "forgot the header" risk and deduplicate the drawer-mount lifecycle to one instance app-wide. This is a candidate for the roadmap, not something changed here.

## Cross-cutting component-level issues

1. **Two disconnected "category" sources of truth** — `MegaMenu`/`SiteFooter` (admin-driven, dynamic) vs. `ShopGrid` (hardcoded, static) vs. `products.ts`'s own `Category` union (source of truth for the data itself). Three places to update for any category change.
2. **No consistent i18n interpolation strategy** — manual `.replace("{{token}}", ...)` in `DeliveryCountdown`, string concatenation in `ProductCard`/`ProductReviews`, plain key lookup elsewhere.
3. **Hardcoded `"SAR"` currency literal** repeated in `CartDrawer` and `ProductCard`, despite the location model supporting multiple currencies per city.
4. **`SiteHeader`'s "Riyadh" hardcoding** contradicts `DeliveryCountdown`'s correct use of `s.location` — two components claiming to show delivery location, one of them wrong/stale.
5. **Locale-independent date formatting** (`toLocaleDateString()` with no locale arg) in `OrderStatusTimeline` and `ProductReviews` — doesn't follow the app's own `en`/`ar` toggle.
