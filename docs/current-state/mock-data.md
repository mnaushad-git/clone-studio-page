# Mock Data & Persistence Inventory

There is no database, no ORM, and no network data-fetching in this application. Every piece of "data" is one of:

1. A hardcoded TypeScript literal (products, cities, promo/loyalty defaults, seeded reviews, staff, couriers)
2. A `localStorage`-backed reactive store built on `useSyncExternalStore`
3. Ephemeral component `useState` that is never persisted at all (e.g. the gift-message composer in `customize.tsx`, the corporate lead form)

## localStorage stores

### `tb.state.v1` — customer-facing store (`src/lib/store.ts`)

Single JSON blob under this key holds:

| Field | Shape | Notes |
|---|---|---|
| `cart` | `CartItem[]` | line items keyed by `productId+size+flavor+inscription` composite |
| `user` | `User \| null` | `{ name?, email?, phone?, birthDate? }` — set by `auth.signIn()`, no password ever stored |
| `addresses` | `Address[]` | includes `isGift`, `isDefault`, gift-recipient fields (`recipientName/Phone`, `timeSlot`, `deliveryDate/Time`) |
| `orders` | `Order[]` | full order snapshots incl. `statusHistory`, `courier` (randomly picked from a 3-entry hardcoded list), `trackingToken`, `recipientConfirmationToken` |
| `promo` | `{code, percent} \| null` | currently applied promo |
| `redeemedPoints` | `number` | loyalty points earmarked for the current checkout |
| `lastOrderId` | `string \| null` | used by `/success` to find the just-placed order |
| `wishlist` | `string[]` | product ids |
| `reviews` | `Review[]` | **seeded with 5 hardcoded reviews** (`seededReviews`) that are always re-merged back in on load (see below) |
| `recentlyViewed` | `string[]` | capped at 12 |
| `location` | `City \| null` | defaults to Riyadh, SA |
| `loyaltyPoints` / `loyaltyHistory` | `number` / `LoyaltyEntry[]` | earn/redeem ledger |
| `recipientConfirmations` | `RecipientConfirmation[]` | gift-recipient address-confirmation tokens |

**Load-time behavior worth flagging**: `load()` in `store.ts` always re-seeds the 5 hardcoded `seededReviews` on top of whatever the user has in localStorage (dedup by id) — meaning these demo reviews can never be permanently deleted by the reviews-admin "delete" action across a fresh load, only hidden until the next full store re-initialization in the same session. This is a subtle mock-data leak worth knowing about before assuming "delete review" is durable.

**Constants embedded directly in this file** (not swappable without a code change):
- `PROMOS` legacy fallback map: `WELCOME10` (10%), `SWEET15` (15%), `TB20` (20%) — used only if a code isn't found in the admin-configured `promos` list.
- `POINTS_PER_DOLLAR = 1`, `POINTS_REDEEM_RATE = 20` (20 pts = SAR 1) — admin `loyalty.redeemRate` overrides this at runtime, but the constant is the hardcoded fallback.
- `RIYADH_AREAS` — 70+ hardcoded Riyadh district names, used as the address-form area picker. No equivalent list exists for the other 7 cities defined in `location.ts`.
- `COURIERS` — 3 hardcoded name/phone pairs randomly assigned to every order at placement time.

### `tb.admin.v1` — admin/config store (`src/lib/admin-store.ts`)

Explicitly documented in the file's own header comment: _"Everything here is frontend-only and ready to be swapped with a FastAPI + Postgres backend later."_ Holds:

| Field | Seed data | Actually consumed by storefront? |
|---|---|---|
| `staff` | 4 hardcoded members (owner, manager, support, kitchen) with real-looking emails | Yes — `adminAuth.signIn` checks against this list |
| `promos` | 3 hardcoded promo codes (`WELCOME10`, `SWEET15`, `TB20`) | **Yes** — `store.ts`'s `promo.apply()` reads this first |
| `zones` | 5 hardcoded Riyadh delivery zones (fee/ETA) | **Not confirmed consumed** outside the admin page itself — checkout fee comes from `settings.defaultDeliveryFee`, not per-zone |
| `slots` | 6 hardcoded time-of-day delivery windows | **Yes** — `delivery.tsx` reads active slots directly |
| `banners` | 2 hardcoded hero/midpage banners | **No** — `index.tsx` (homepage) does not read this at all |
| `categories` | 6 hardcoded categories mirroring `products.ts`'s static `Category` union | Read by `MegaMenu`/`SiteFooter`; **not** read by `ShopGrid`'s filter sidebar (separate hardcoded `CATEGORIES` list there) — two sources of truth |
| `paymentMethods` | 5 hardcoded methods (card, Apple Pay, Mada, STC Pay, COD-disabled) | **Yes** — `payment.tsx` reads active methods |
| `loyalty` | `{enabled, pointsPerSar, redeemRate, signupBonus, birthdayBonus}` | `redeemRate` **yes**; `enabled` gate not confirmed enforced anywhere |
| `settings` | brand name, support contact, currency, `taxRate`, `defaultDeliveryFee`, `freeDeliveryThreshold`, `minOrder`, languages, operating hours, socials, `maintenanceMode`, `guestCheckout` | `taxRate`/`minOrder`/`defaultDeliveryFee`/`freeDeliveryThreshold` **yes** (checkout math); `maintenanceMode` yes (root banner); `guestCheckout`/`languages`/`socials` not confirmed enforced |
| `productOverrides` | empty by default (`{}`) | **Yes** — `product.$id.tsx` and `admin.products.tsx` both read/write this, keyed by product id from `products.ts` |
| `homepageSections` | 8 hardcoded section entries with visibility/order | **No** — `index.tsx` does not read this |
| `notifications` | 3 hardcoded seed notifications | Admin-panel only (bell icon) |
| `adminSession` | `null` by default | Set entirely client-side by `adminAuth.signIn()` — see [frontend-architecture.md](./frontend-architecture.md) for the security implications |
| `theme` | `DEFAULT_ADMIN_THEME` + 5 presets | Admin-panel-only cosmetic CSS variables |

## Static/hardcoded data files (not stores — no persistence, no mutation)

### `src/lib/products.ts` — the product catalog

- 28 products hardcoded as a literal array, spanning categories `cupcakes | cakes | chocolates | donuts | gifts | extras`.
- Each product has: id, name, price, image (static import), optional `thumbs[]`, `sizes[]` (with price `delta`), `flavors[]`, `description`, `isNew`, `occasions[]`, `recipients[]`.
- `productMap`/`getProduct(id)` — simple lookup helpers.
- `featured` — derived slices (`hero`, `gifts`, `divine`, `chocolates`, `extras`, `new`) computed once at module load via `.filter()`/`.slice()` on the static array — **not** admin-configurable (the homepage's "featured" rails always show the same 4 cupcakes regardless of admin `productOverrides.featured` flags).
- `OCCASIONS` (6) and `RECIPIENTS` (4) are hardcoded const tuples, plus slug helper functions.
- **This file is the single point of truth for what products exist.** Admin `productOverrides` layer cosmetic/pricing changes on top but cannot add or remove a product — there's no "add new product" capability anywhere in the admin UI, only edit-existing.

### `src/lib/location.ts`

- `CITIES` — 8 hardcoded cities across Saudi Arabia, UAE, Kuwait, Qatar, Egypt, each with a `sameDayCutoffHour` and `currency`.
- `FLAGS` — emoji flag lookup by country code.
- `nextDeliveryWindow()` — pure function computing same-day/next-day messaging from the current wall-clock hour vs. a city's cutoff.
- **Only Riyadh is actually reachable in the UI today** — `SiteHeader`'s location chip is hardcoded to "Riyadh" text + 🇸🇦 emoji and never reads `useStore(s => s.location)`, so the multi-city model exists in data but has no UI entry point to actually switch cities (see [gap-analysis.md](./gap-analysis.md)).

### Other hardcoded literals worth knowing about

- `src/lib/store.ts`: `seededReviews` (5 reviews), `COURIERS` (3 couriers), `RIYADH_AREAS` (70+ areas), `PROMOS` legacy map.
- `src/lib/admin-store.ts`: all seed arrays listed in the table above, plus `ADMIN_THEME_PRESETS` (5 named color themes).
- `src/components/MegaMenu.tsx`: `CAT_IMG` hardcoded category→image map (with `extras` reusing the `gifts` image as a placeholder gap).
- `src/components/ShopGrid.tsx`: `CATEGORIES`, `OCCASION_LABEL_KEYS`, `RECIPIENT_LABEL_KEYS`, `PRICE_BUCKETS` (four fixed price ranges).
- `src/components/SiteFooter.tsx`: "Company"/"Help" link columns are hardcoded label arrays pointing at `href="#"` (dead links); payment badge row (`VISA/AMEX/PayPal/GPay`) is static, non-interactive text.

## What this means for a future backend

Nearly every one of these hardcoded arrays/constants maps cleanly onto an obvious future database table (`products`, `categories`, `promo_codes`, `delivery_zones`, `delivery_slots`, `staff`, `orders`, `reviews`, `addresses`, `banners`). The admin CRUD screens already model the right shape of operations (add/update/remove) — the work is replacing the `localStorage` read/write in each `*Store` object with real API calls, not redesigning the admin UI. See [roadmap.md](./roadmap.md) for a suggested migration sequence.
