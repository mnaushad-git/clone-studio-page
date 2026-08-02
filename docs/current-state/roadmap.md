# Proposed Implementation Roadmap

_This is a proposal for sequencing future work — nothing in this document has been implemented. It exists to align on approach before any backend/architectural work begins._

## Guiding principle

The existing UI should be treated as the **product specification**. Every admin CRUD screen, every checkout step, every store selector already models the right shape of a real system — the work ahead is almost entirely about giving that shape a real, secure, persistent backend, not redesigning the frontend. Where this audit found a disconnect (e.g., `/admin/content` not affecting the homepage), the fix should make the UI's implied behavior real, not remove the UI.

## 1. Repository strengths

- **Remarkably complete UI surface for a demo-stage app.** ~40 routes across storefront and admin, consistent shadcn/ui design system, working bilingual (en/ar) RTL support — this is far more built-out than a typical prototype.
- **The mock-data layer is well-organized, not scattered.** Two clear stores (`store.ts`, `admin-store.ts`), consistent `useSyncExternalStore` pattern, clean selector functions — this will migrate to a real API cleanly because the read/write boundaries are already well-defined per domain (cart, orders, promos, staff, etc.).
- **Admin config genuinely does drive storefront behavior in the important places** — promo codes, delivery slots, tax rate, loyalty redeem rate, and per-product overrides are all real, live-wired connections, not just decoration. The admin panel is not purely cosmetic.
- **Supabase is already provisioned** (real project ID, publishable key, correctly structured client/server/middleware scaffolding) — the on-ramp to a real backend is partially built and follows Supabase's own recommended patterns (RLS-aware client separation, JWT claims middleware).
- **i18n/RTL is a first-class concern already**, not bolted on — most components correctly use logical CSS properties and a typed translation-key system.
- **TypeScript strict mode + a modern, well-chosen stack** (React 19, TanStack Start/Router/Query, Tailwind v4) — no outdated dependencies or deprecated patterns found.

## 2. Repository weaknesses

- **No real authentication anywhere** (customer or admin) — this is the single largest gap and touches every other feature (orders, staff, payments all assume "whoever is in this browser" is a trusted identity).
- **No real persistence** — all data lives in one browser's `localStorage`; nothing survives a cleared cache, a different device, or a second concurrent user.
- **Several admin screens are disconnected from the storefront they claim to control** (see gap-analysis.md §2) — before adding a real backend, these need to be either wired up or explicitly scoped out.
- **No automated tests** — any backend migration will be done "blind" without regression coverage unless tests are introduced alongside it.
- **No CI/CD pipeline** — nothing enforces lint/type-check/tests today; a migration this size should not proceed without at least basic CI gating.

## 3. Risks

| Risk | Why it matters |
|---|---|
| **Treating this as "just add a database" underestimates the auth rework.** Every store mutation (`cart.add`, `orders.place`, `staffStore.update`, etc.) currently assumes trusted, single-user, synchronous local access. Each one needs to become an authorized, validated, server-side operation — this is the largest single piece of work, not the database schema itself. |
| **Multi-tenancy is a design decision, not a migration detail.** `admin.customers.tsx`'s own comment shows the current mental model is "one browser = one customer." A real backend needs an explicit decision on how customer accounts, guest checkout, and admin staff accounts relate to each other and to Supabase Auth's user model before any table is created. |
| **Payment integration carries compliance weight.** The current `payment.tsx` form shape (raw card fields) must not be the template for the real integration — a real PCI-compliant flow (hosted fields / tokenization via a provider) needs to be chosen early since it changes the checkout UI's data flow, not just its backend. |
| **RLS (Row Level Security) design in Supabase is easy to get wrong silently.** Given `client.server.ts`'s explicit warning that the service-role client "bypasses RLS," any server function written carelessly against the admin client instead of the user-scoped one could reintroduce the exact same "any user can access anything" problem this migration is meant to fix. |
| **Lovable sync constraints.** Per `AGENTS.md`, this branch is synced with the Lovable editor — force-pushes, rebases, and amends on pushed history will desync the Lovable project. Any backend work should stay in normal forward commits, and any large refactor (e.g., hoisting `SiteHeader`/`SiteFooter` into `__root.tsx`) should be coordinated with however the team continues to use Lovable going forward (see open questions). |
| **Feature scope creep during "just wire up the backend."** Because so many gaps are visible now (dead footer links, disconnected admin categories, discarded gift-message feature), there will be temptation to "fix everything" during the backend migration. Recommend explicitly triaging gap-analysis.md into "must fix now" vs. "backlog" before starting implementation. |

## 4. Recommended implementation sequence

This sequence prioritizes de-risking authentication and data-integrity first, since nearly every later step depends on "who is making this request" being a real, verifiable answer.

1. **Decide the data/tenancy model** (see open questions below) — customer accounts vs. guest checkout, staff/role model, single-tenant vs. multi-tenant. This is a decision, not code, and should happen before any schema is written.
2. **Stand up real authentication** — customer auth (likely Supabase Auth, given it's already provisioned) and a genuinely separate, server-verified admin/staff auth with real RBAC enforcement server-side (not just hidden UI). This unblocks everything else and directly closes the highest-severity findings in gap-analysis.md §1.
3. **Design and migrate the core schema**, informed directly by the existing store shapes (they're already close to right): `products`, `categories`, `orders` + `order_items`, `addresses`, `promo_codes`, `delivery_zones`, `delivery_slots`, `reviews`, `staff`, `loyalty_ledger`. Reuse the existing TypeScript types in `store.ts`/`admin-store.ts` as the starting point for schema design — they are already well-shaped.
4. **Replace the two localStorage stores' internals with real API calls**, one domain at a time, keeping the existing `useStore`/`useAdmin` selector call sites in components unchanged where possible (i.e., swap the implementation behind `cart.add()` etc., not every call site) — this limits blast radius on the UI layer that already works.
5. **Wire the currently-disconnected admin screens to real effect** (banners/homepage sections → actual homepage rendering, categories → actual product categorization, delivery zones → actual fee calculation, product stock → actual decrement on order) as part of the same pass that gives them a real table, since "make it real" and "make it work" become the same task once there's a backend.
6. **Replace simulated checkout steps with real integrations**: a real payment provider (tokenized, PCI-compliant), a real email/SMS provider for OTP/password-reset/order notifications, and a real courier/fulfillment integration or at minimum a genuine order-status webhook instead of the client-side `setTimeout` auto-advance.
7. **Introduce automated testing** alongside the migration — at minimum integration tests for cart/checkout math and admin CRUD, given how many of this audit's findings (disconnected admin controls, unenforced usage limits) were the kind of regression a test suite exists to catch.
8. **Set up CI** (lint, typecheck, test) gating merges before the migration branch grows large.
9. **Close remaining UX/data-consistency gaps** from gap-analysis.md §3–§4 (dead footer links, hardcoded "Riyadh" header, RTL mega-menu direction, currency literal) — lower risk, can be scheduled opportunistically once the backend work is underway.

## 5. Questions that need clarification before development begins

1. **Tenancy model**: Is this application meant to serve a single bakery brand ("Terrific Bites") only, or is a multi-tenant/white-label model ever in scope? This materially changes schema design (e.g., does every table need a `tenant_id`?).
2. **Customer accounts**: Should customer identity be full Supabase Auth accounts (email/password, OTP, social), or is a lighter "guest + saved address" model acceptable long-term? The current UI supports both a full account flow and guest checkout gating in `CartDrawer` — which is the intended long-term default?
3. **Staff/role model**: What should the real permission boundaries be per role (`owner/admin/manager/support/kitchen`)? The UI already defines these five roles but enforces none of them — a real RBAC matrix (who can edit staff, settings, orders, content) needs to be specified.
4. **Multi-city/multi-currency**: Is expansion beyond Riyadh (the other 7 cities already modeled in `location.ts`) an active near-term goal, or should that data model be simplified/removed if Saudi Arabia (Riyadh) is the only real market for now?
5. **Payment provider**: Is there already a preferred payment gateway/PSP for the Saudi/GCC market (e.g., Moyasar, HyperPay, Tap, PayTabs, or a global provider with regional support), given the existing UI already lists Mada/STC Pay/Apple Pay as method options?
6. **Notification channels**: For OTP, password reset, and order-status updates — is SMS required (common expectation in the GCC market) in addition to email, and is there a preferred provider?
7. **Lovable workflow going forward**: Will active development continue to flow through the Lovable editor in parallel with direct backend engineering, or is this the point where the team moves to a standard local/CI-based workflow? This affects how safely larger structural refactors (e.g., hoisting header/footer into the root layout) can be done without conflicting with Lovable-side prompt-driven changes.
8. **Which gap-analysis findings are "keep as-is for now" vs. "must fix"?** In particular: the discarded gift-message feature (§3.1), disconnected admin content/categories/zones (§2), and the dead footer links (§3.6) — are any of these intentionally out of scope, or should all be treated as backlog bugs once a backend exists?
9. **Existing demo data**: Should the seeded reviews, staff, promo codes, and product catalog become real seed/fixture data in the new backend, or are they purely placeholder content to be replaced entirely with real bakery data before launch?

## Related documents

[project-overview.md](./project-overview.md) · [folder-structure.md](./folder-structure.md) · [routes.md](./routes.md) · [mock-data.md](./mock-data.md) · [components.md](./components.md) · [frontend-architecture.md](./frontend-architecture.md) · [gap-analysis.md](./gap-analysis.md)
