# Final local validation report

> **Historical record** of local development closure. Its section 10 assumed the shared VPS
> `187.127.159.23`; deployment now targets client staging on the dedicated VPS `2.25.11.35`,
> see [hostinger-deployment-package.md](hostinger-deployment-package.md).

Terrific Bites MVP, local development closure, 9 November 2026. Nothing here has been committed,
pushed or deployed. Baseline: commit `e58e072`.

All results come from an isolated native stack (PostgreSQL 55441, Odoo 19 on 18069, its own Memurai
on 16379) rebuilt from empty for this iteration. The shared Odoo, PostgreSQL and Memurai services,
myMakan and Maskan were not modified.

## Outcome

The variant price defect is fixed and verified on real Odoo. Every local acceptance check passes.
**Docker images and Compose have not been built or run**, by design; that's the first task on the VPS.

| Definition of done | Status | Evidence |
|---|---|---|
| 26 products and 55 variants with verified prices | Met | Section 1 |
| Repeated imports and syncs preserve prices | Met | Section 2 |
| Storefront and Odoo sales-order totals reconcile | Met | Section 3 |
| Worker retries and duplicate-order safeguards pass | Met | Section 3 |
| Critical regression tests pass | Met | Section 4 |
| Production security findings assessed | Met | Section 5 |
| Frontend runs independently of Lovable | Met | Section 5 |
| Deployment package ready for Docker validation | Met, unbuilt | Section 6 |
| No application defect blocks Stage A | Met | Section 7 |

## What was wrong, and the fix

Three separate faults could lose a size price:

1. The importer never wrote `price_extra`, so Odoo sold every size at the base price.
2. If the sync's attribute lookup failed, it silently fell back to the base price.
3. Incremental sync missed price changes, because editing `list_price` or `price_extra` doesn't
   change a variant's `write_date`.

Now the importer sets `price_extra` on `product.template.attribute.value`, Odoo's own mechanism.
No pricelist rules are needed. It writes only while the value is zero and never overwrites a
different one. The sync publishes Odoo's computed `lst_price`, read in full on every run, and
compares every approved SKU first. Any difference fails the run before anything is published.

## 1. Variant price reconciliation: all 55

Expected, Odoo `lst_price`, PostgreSQL and the public API, after the final sync.
55 of 55 match everywhere; 28 have a size price above base.
Odoo's own pricelist engine (`_get_product_price`, no pricelist rules) also returned the approved
price for all 55.

| Product | Variant | SKU | Base | Expected | Odoo | PostgreSQL | API |
|---|---|---|---|---|---|---|---|
| Swiss Frosting | PACK OF 6 | `TB-CUP-001-PACKOF6` | 12.50 | 12.50 | 12.50 | 12.50 | 12.50 |
| Swiss Frosting | PACK OF 12 | `TB-CUP-001-PACKOF12` | 12.50 | 23.75 | 23.75 | 23.75 | 23.75 |
| Moose Cream | PACK OF 6 | `TB-CUP-002-PACKOF6` | 14.00 | 14.00 | 14.00 | 14.00 | 14.00 |
| Moose Cream | PACK OF 12 | `TB-CUP-002-PACKOF12` | 14.00 | 26.60 | 26.60 | 26.60 | 26.60 |
| Butter Frosting | PACK OF 6 | `TB-CUP-003-PACKOF6` | 11.00 | 11.00 | 11.00 | 11.00 | 11.00 |
| Butter Frosting | PACK OF 12 | `TB-CUP-003-PACKOF12` | 11.00 | 20.90 | 20.90 | 20.90 | 20.90 |
| Light Sponge | PACK OF 6 | `TB-CUP-004-PACKOF6` | 9.50 | 9.50 | 9.50 | 9.50 | 9.50 |
| Light Sponge | PACK OF 12 | `TB-CUP-004-PACKOF12` | 9.50 | 18.05 | 18.05 | 18.05 | 18.05 |
| Buttercream Cake | 6 INCH / Vanilla | `TB-CAK-001-6INCH-VANILLA` | 300.00 | 300.00 | 300.00 | 300.00 | 300.00 |
| Buttercream Cake | 6 INCH / Chocolate | `TB-CAK-001-6INCH-CHOCOLATE` | 300.00 | 300.00 | 300.00 | 300.00 | 300.00 |
| Buttercream Cake | 9 INCH / Vanilla | `TB-CAK-001-9INCH-VANILLA` | 300.00 | 380.00 | 380.00 | 380.00 | 380.00 |
| Buttercream Cake | 9 INCH / Chocolate | `TB-CAK-001-9INCH-CHOCOLATE` | 300.00 | 380.00 | 380.00 | 380.00 | 380.00 |
| Birthday Pair Cups | STANDARD | `TB-GIF-001-STANDARD` | 22.00 | 22.00 | 22.00 | 22.00 | 22.00 |
| Birthday Pair Cups | DELUXE | `TB-GIF-001-DELUXE` | 22.00 | 37.00 | 37.00 | 37.00 | 37.00 |
| Butter Frosting Delight | STANDARD | `TB-GIF-002-STANDARD` | 18.00 | 18.00 | 18.00 | 18.00 | 18.00 |
| Butter Frosting Delight | DELUXE | `TB-GIF-002-DELUXE` | 18.00 | 33.00 | 33.00 | 33.00 | 33.00 |
| Cream & Cheese Donut | SINGLE | `TB-DON-001-SINGLE` | 8.00 | 8.00 | 8.00 | 8.00 | 8.00 |
| Cream & Cheese Donut | PACK OF 6 | `TB-DON-001-PACKOF6` | 8.00 | 40.00 | 40.00 | 40.00 | 40.00 |
| Whisk & Whimsy Cupcake | STANDARD | `TB-GIF-003-STANDARD` | 15.00 | 15.00 | 15.00 | 15.00 | 15.00 |
| Whisk & Whimsy Cupcake | DELUXE | `TB-GIF-003-DELUXE` | 15.00 | 30.00 | 30.00 | 30.00 | 30.00 |
| Sprinkle Cupcakes | PACK OF 6 | `TB-CUP-005-PACKOF6` | 4.50 | 4.50 | 4.50 | 4.50 | 4.50 |
| Sprinkle Cupcakes | PACK OF 12 | `TB-CUP-005-PACKOF12` | 4.50 | 8.55 | 8.55 | 8.55 | 8.55 |
| Cherry Sprinkle | PACK OF 6 | `TB-CUP-006-PACKOF6` | 4.50 | 4.50 | 4.50 | 4.50 | 4.50 |
| Cherry Sprinkle | PACK OF 12 | `TB-CUP-006-PACKOF12` | 4.50 | 8.55 | 8.55 | 8.55 | 8.55 |
| Pink Whip | PACK OF 6 | `TB-CUP-007-PACKOF6` | 4.50 | 4.50 | 4.50 | 4.50 | 4.50 |
| Pink Whip | PACK OF 12 | `TB-CUP-007-PACKOF12` | 4.50 | 8.55 | 8.55 | 8.55 | 8.55 |
| Confetti Whip | PACK OF 6 | `TB-CUP-008-PACKOF6` | 4.50 | 4.50 | 4.50 | 4.50 | 4.50 |
| Confetti Whip | PACK OF 12 | `TB-CUP-008-PACKOF12` | 4.50 | 8.55 | 8.55 | 8.55 | 8.55 |
| Chocolate Truffle | SMALL BOX | `TB-CHO-001-SMALLBOX` | 6.99 | 6.99 | 6.99 | 6.99 | 6.99 |
| Chocolate Truffle | LARGE BOX | `TB-CHO-001-LARGEBOX` | 6.99 | 12.58 | 12.58 | 12.58 | 12.58 |
| Hazelnut Praline | SMALL BOX | `TB-CHO-002-SMALLBOX` | 7.50 | 7.50 | 7.50 | 7.50 | 7.50 |
| Hazelnut Praline | LARGE BOX | `TB-CHO-002-LARGEBOX` | 7.50 | 13.50 | 13.50 | 13.50 | 13.50 |
| Ganache Bites | SMALL BOX | `TB-CHO-003-SMALLBOX` | 8.25 | 8.25 | 8.25 | 8.25 | 8.25 |
| Ganache Bites | LARGE BOX | `TB-CHO-003-LARGEBOX` | 8.25 | 14.85 | 14.85 | 14.85 | 14.85 |
| Salted Caramel | SMALL BOX | `TB-CHO-004-SMALLBOX` | 7.25 | 7.25 | 7.25 | 7.25 | 7.25 |
| Salted Caramel | LARGE BOX | `TB-CHO-004-LARGEBOX` | 7.25 | 13.05 | 13.05 | 13.05 | 13.05 |
| Mint Delight | SMALL BOX | `TB-CHO-005-SMALLBOX` | 6.50 | 6.50 | 6.50 | 6.50 | 6.50 |
| Mint Delight | LARGE BOX | `TB-CHO-005-LARGEBOX` | 6.50 | 11.70 | 11.70 | 11.70 | 11.70 |
| Orange Zest | SMALL BOX | `TB-CHO-006-SMALLBOX` | 6.75 | 6.75 | 6.75 | 6.75 | 6.75 |
| Orange Zest | LARGE BOX | `TB-CHO-006-LARGEBOX` | 6.75 | 12.15 | 12.15 | 12.15 | 12.15 |
| Roasted Almond | SMALL BOX | `TB-CHO-007-SMALLBOX` | 7.99 | 7.99 | 7.99 | 7.99 | 7.99 |
| Roasted Almond | LARGE BOX | `TB-CHO-007-LARGEBOX` | 7.99 | 14.38 | 14.38 | 14.38 | 14.38 |
| White Dream | SMALL BOX | `TB-CHO-008-SMALLBOX` | 6.25 | 6.25 | 6.25 | 6.25 | 6.25 |
| White Dream | LARGE BOX | `TB-CHO-008-LARGEBOX` | 6.25 | 11.25 | 11.25 | 11.25 | 11.25 |
| Berry Truffle | SMALL BOX | `TB-CHO-009-SMALLBOX` | 7.99 | 7.99 | 7.99 | 7.99 | 7.99 |
| Berry Truffle | LARGE BOX | `TB-CHO-009-LARGEBOX` | 7.99 | 14.38 | 14.38 | 14.38 | 14.38 |
| Fanky Donut | SINGLE | `TB-EXT-001-SINGLE` | 4.89 | 4.89 | 4.89 | 4.89 | 4.89 |
| Fanky Donut | PACK | `TB-EXT-001-PACK` | 4.89 | 19.56 | 19.56 | 19.56 | 19.56 |
| Icecream Cone | SMALL (3OZ) | `TB-EXT-002-SMALL3OZ` | 5.49 | 5.49 | 5.49 | 5.49 | 5.49 |
| Icecream Cone | MEDIUM (11OZ) | `TB-EXT-002-MEDIUM11OZ` | 5.49 | 8.49 | 8.49 | 8.49 | 8.49 |
| Icecream Cone | LARGE (16OZ) | `TB-EXT-002-LARGE16OZ` | 5.49 | 11.49 | 11.49 | 11.49 | 11.49 |
| Mini Cheesecake | SINGLE | `TB-EXT-003-SINGLE` | 6.29 | 6.29 | 6.29 | 6.29 | 6.29 |
| Mini Cheesecake | PACK | `TB-EXT-003-PACK` | 6.29 | 25.16 | 25.16 | 25.16 | 25.16 |
| Donuts Pair | SINGLE | `TB-EXT-004-SINGLE` | 7.89 | 7.89 | 7.89 | 7.89 | 7.89 |
| Donuts Pair | PACK | `TB-EXT-004-PACK` | 7.89 | 31.56 | 31.56 | 31.56 | 31.56 |

## 2. Repeated import and synchronization

**Berry Truffle LARGE BOX stayed SAR 14.38 in Odoo, PostgreSQL and the API at every clean
checkpoint.** In the tests below where Odoo was deliberately changed, PostgreSQL and the API held
14.38 throughout.

| Step | Result |
|---|---|
| Import 1, empty Odoo | SUCCEEDED, 137 created, 27 `price_extra` set, 55 of 55 match |
| 3 full syncs through the worker | SUCCEEDED; prices updated 55 (seed to Odoo-sourced), then unchanged 55 and 55 |
| Imports 2 and 3 | SUCCEEDED, 0 created, 0 updated, 164 skipped |
| `--reconcile` | CLEAN, 164 items, 55 of 55 prices |
| Stop and restart API, worker, Beat and Odoo, then 2 syncs | SUCCEEDED, 55 unchanged, 55 of 55 |
| Sync after the full regression, 2 runs | SUCCEEDED, 55 unchanged, 55 of 55 |

Failure paths, deliberately triggered on real Odoo:

| Injected | Sync | Import | Published price |
|---|---|---|---|
| `price_extra` changed to 9.99 (Odoo 17.98) | FAILED, named the variant with expected 14.38 and actual 17.98 | FAILED, value not overwritten | Stayed 14.38 |
| `price_extra` reset to 0 (Odoo 7.99) | FAILED, named expected 14.38 and actual 7.99 | Repaired, 1 updated | Stayed 14.38 |
| Price write committed, client timed out | Not applicable | First run FAILED (1 item); retry 0 writes, SUCCEEDED | Stayed 14.38 |

## 3. Real Odoo orders and financial reconciliation

`verify`: 45 of 45. Paid orders reached confirmed sale orders through the real API and worker
(for example `TB-QFXJCZ`, `S00001`). Re-delivered events reused the order, 8 raw concurrent creates
committed once, and 6 concurrent pushes agreed on one order. An unsyncable order retried to the
limit of 4, dead-lettered, and an operator retry synced it once. With Odoo stopped, the API still
took orders, and they synced exactly once on recovery. Demo orders were marked `simulated`, and
Odoo's order count stayed at 6.

`verify-financials`: 119 of 119, covering SAR, the SAR pricelist, 15% VAT-inclusive pricing,
discounts, delivery fees, customization and rounding.

| Scenario | Storefront | Odoo | Storefront VAT | Odoo VAT | Currency |
|---|---|---|---|---|---|
| single item, delivery charged | 315.00 | 315.00 | 41.09 | 41.09 | SAR |
| multiple quantities with inscription | 74.85 | 74.85 | 9.76 | 9.76 | SAR |
| mixed variants of one product | 76.28 | 76.28 | 9.95 | 9.95 | SAR |
| percentage discount, odd amounts | 138.47 | 138.47 | 18.06 | 18.06 | SAR |
| fixed discount with delivery | 597.50 | 597.50 | 77.93 | 77.93 | SAR |
| zero delivery fee | 300.00 | 300.00 | 39.13 | 39.13 | SAR |
| zero delivery with discount | 45.16 | 45.16 | 5.89 | 5.89 | SAR |
| rounding stress, quantity 1 | 31.54 | 31.54 | 4.11 | 4.11 | SAR |
| rounding stress, quantity 3 | 64.62 | 64.62 | 8.43 | 8.43 | SAR |
| rounding stress, quantity 9 | 163.86 | 163.86 | 21.37 | 21.37 | SAR |

## 4. Test results

| Suite | Result |
|---|---|
| Backend pytest (`native_stack.py test`) | 644 passed, 4 skipped |
| Odoo integration (`verify`) | 45 of 45 |
| Financial reconciliation (`verify-financials`) | 119 of 119 |
| Browser journey (headless, customer and admin) | 40 of 40 |
| Frontend vitest | 68 passed, 8 files |
| Production build (`vite build`) | Succeeded |
| Standalone production server | `/`, `/shop`, `/product/choc-berry`, `/admin/login`, footer logo and social image all 200 |
| ruff, mypy, tsc | Clean (mypy 236 files) |
| ESLint | 0 errors, 855 warnings (848 are auto-fixable formatting, deliberately left) |

The 4 skipped tests are opt-in checks against the shared Odoo, left off on purpose. The browser
journey ran against the dev server. The production build had the HTTP checks above, not the full
journey. `verify`, `verify-financials` and the browser journey ran before two final small backend
edits (a health check and an error-message prefix); pytest, ruff, mypy and the price verification
were rerun on the final code.

## 5. Security

| Check | Result |
|---|---|
| Python dependencies (`pip-audit`, 68 packages installed) | No known vulnerabilities |
| npm production dependencies | 1 high: `zod` 3.25.76 (accepted, below) |
| Secrets in tracked or untracked files (645 scanned) | None. Hits were test fixtures, identifiers and doc placeholders |
| Tracked `.env`, `.env.production` | Publishable Supabase values and public URLs only |
| Odoo credentials by service | API, Beat and migrations hold none and refuse to start with one. Worker has the order-sync login, import has the catalogue login. The order-sync user is non-admin and blocked from creating products (verified on real Odoo) |
| Production-write safeguards | Order push fixed to stub in Compose. Writes refused unless `ODOO_WRITE_APPROVED_TARGET` names the exact URL and database |
| Local mode can't reach production | Same guard. The native stack's approved target is its own loopback address only |
| Lovable hosting dependency | None at runtime. Social image and `@Lovable` metadata removed from the HTML |
| Frontend assets | Footer logo served from the local bundle, 200 |

Accepted residual risks, for your sign-off:

- **`zod` high advisory (GHSA-mrhx-c7xc-m3w5).** Memory exhaustion on oversized input. The only
  fix is a major upgrade to 4.x. zod runs only in browser forms (3 routes) with no server
  functions, so an attacker could only affect their own tab. Upgrade after launch.
- **Dormant Lovable code.** `lovable-error-reporting.ts` is in the bundle and does nothing without
  the editor's script. `@lovable.dev/vite-tanstack-config` is an npm build dependency and is kept
  so the Lovable editor still works on this branch.
- **Supabase project URL in the bundle.** A public value; the project is provisioned but unwired.

## 6. Hostinger deployment package

Prepared and reviewed; no container has been built or run. Static checks only: `bash -n` on all 11
scripts, Compose YAML parsed, all 23 Compose variables present in the template, and
`package-lock.json` in sync. Every long-running service has a restart policy. Beat has no container
health check and is covered by the worker heartbeat alert. The frontend's is in its image.

Corrected in this iteration: Odoo's address in the env template; capacity thresholds now 4.5 GB and
25 GB; a catalogue import section; the price-change procedure; the status note on Docker validation;
removal of the instruction to join the Docker group; and a monitoring alert when a sync is refused
over prices.

## 7. Remaining blockers and decisions

No application defect blocks the Stage A demo. Before or during deployment:

| Item | Owner | Blocks |
|---|---|---|
| Docker build and run, first time anywhere | VPS step | Deployment |
| VPS capacity, ports and Caddy layout unknown until discovery | VPS step | Deployment |
| How deployment gets Docker access, given no Docker group or unrestricted sudo | You | Deployment |
| Written authorization for the catalogue import into production Odoo | You | Catalogue import |
| VPS snapshot confirmed in hPanel | You | Deployment |
| `odoo:19.0` is a floating tag; pin it to a digest after pulling. Tested locally on 19.0-20260720 | VPS step | Recommended |
| Off-site backup destination | You | Before real data |
| Price-change procedure: Odoo changes also need `products.json`, or sync refuses | You | Before staff edit prices |
| Client finance approval of VAT and delivery rules; real payments, notifications, ZATCA | Client | Live commerce only |

Local only: PID 16400, an orphaned helper from the isolated PostgreSQL that crashed on 8 November,
still holds port 55440. It doesn't affect this work and should clear on reboot, or can be ended with
your approval. `.local-integration/pg` is left intact. To restart the isolated stack, set
`TB_NATIVE_STATE=$PWD/.local-integration/rebuild-20261109` and `TB_NATIVE_PG_PORT=55441`.

## 8. Files

Changed in this iteration:

- `backend/app/services/catalogue/variant_pricing.py` (new)
- `backend/app/services/catalogue/odoo_import_service.py`
- `backend/app/services/catalogue/odoo_catalogue_sync_service.py`
- `backend/app/integrations/odoo/repositories/products.py`
- `backend/app/integrations/odoo/repositories/attributes.py`
- `backend/app/services/ops/health_monitor.py`
- `backend/app/scripts/import_odoo_catalogue.py`
- `backend/tests/unit/test_variant_pricing.py` (new)
- `backend/tests/integration/test_odoo_import_service.py`
- `backend/tests/integration/test_odoo_catalogue_sync_service.py`
- `backend/tests/integration/test_health_monitor.py`
- `deploy/native/native_stack.py`
- `deploy/native/verify_variant_prices.py` (new)
- `deploy/.env.prod.example`
- `deploy/scripts/vps-discovery.sh`
- `docs/deployment/hostinger-deployment-package.md`
- `docs/deployment/vps-access-and-discovery.md`
- `docs/deployment/native-integration.md`
- `docs/deployment/final-local-validation-report.md` (new)
- `docs/integrations/odoo-catalogue-variant-model.md`
- `src/routes/__root.tsx`
- `public/og-image.png` (new)

All 111 uncommitted paths since the baseline (`M` modified, `D` deleted, `??` new):

- `??` `.gitattributes`
- `M` `.gitignore`
- `M` `.prettierrc`
- `M` `backend/.env.example`
- `M` `backend/app/api/v1/endpoints/orders.py`
- `M` `backend/app/core/config.py`
- `M` `backend/app/core/exceptions.py`
- `??` `backend/app/core/rate_limit.py`
- `??` `backend/app/db/alembic/versions/0017_outbox_retry_and_dead_letter.py`
- `M` `backend/app/integrations/odoo/order_push.py`
- `??` `backend/app/integrations/odoo/order_reconciliation.py`
- `M` `backend/app/integrations/odoo/repositories/attributes.py`
- `M` `backend/app/integrations/odoo/repositories/products.py`
- `??` `backend/app/integrations/odoo/write_target_guard.py`
- `M` `backend/app/main.py`
- `M` `backend/app/models/orders/order_outbox_event.py`
- `M` `backend/app/repositories/orders/order_outbox_repository.py`
- `M` `backend/app/scripts/import_odoo_catalogue.py`
- `M` `backend/app/services/admin/order_admin_service.py`
- `M` `backend/app/services/catalogue/odoo_catalogue_sync_service.py`
- `M` `backend/app/services/catalogue/odoo_import_planning.py`
- `M` `backend/app/services/catalogue/odoo_import_service.py`
- `??` `backend/app/services/catalogue/variant_pricing.py`
- `M` `backend/app/services/checkout/odoo_sync_service.py`
- `M` `backend/app/services/checkout/payment_service.py`
- `M` `backend/app/services/checkout/pricing_service.py`
- `M` `backend/app/services/ops/health_monitor.py`
- `M` `backend/pyproject.toml`
- `M` `backend/tests/conftest.py`
- `M` `backend/tests/integration/test_checkout_pricing_service.py`
- `M` `backend/tests/integration/test_e2e_catalogue_and_order_lifecycle.py`
- `M` `backend/tests/integration/test_health_monitor.py`
- `M` `backend/tests/integration/test_odoo_catalogue_sync_service.py`
- `M` `backend/tests/integration/test_odoo_import_service.py`
- `??` `backend/tests/integration/test_order_sync_reliability.py`
- `M` `backend/tests/integration/test_orders_api.py`
- `??` `backend/tests/integration/test_payment_stage_guard.py`
- `??` `backend/tests/integration/test_rate_limits.py`
- `M` `backend/tests/unit/odoo/test_live_order_pusher.py`
- `M` `backend/tests/unit/odoo/test_odoo_import_planning.py`
- `??` `backend/tests/unit/odoo/test_order_push_idempotency.py`
- `??` `backend/tests/unit/odoo/test_order_reconciliation.py`
- `M` `backend/tests/unit/test_approval_gate.py`
- `??` `backend/tests/unit/test_credential_separation.py`
- `M` `backend/tests/unit/test_production_settings.py`
- `M` `backend/tests/unit/test_stub_odoo_order_pusher.py`
- `??` `backend/tests/unit/test_variant_pricing.py`
- `M` `bun.lock`
- `M` `data/catalogue/catalogue-business-approvals.json`
- `M` `deploy/.env.prod.example`
- `M` `deploy/caddy/api.terrific-bites.caddy`
- `??` `deploy/caddy/terrific-bites.caddy`
- `M` `deploy/docker-compose.prod.yml`
- `??` `deploy/frontend.Dockerfile`
- `??` `deploy/frontend.Dockerfile.dockerignore`
- `??` `deploy/local/`
- `??` `deploy/native/`
- `??` `deploy/odoo/`
- `??` `deploy/postgres-init/`
- `??` `deploy/scripts/Run-VpsDiscovery.ps1`
- `??` `deploy/scripts/backup-all.sh`
- `M` `deploy/scripts/backup-db.sh`
- `M` `deploy/scripts/measure-product-page.sh`
- `M` `deploy/scripts/migrate.sh`
- `M` `deploy/scripts/monitor.sh`
- `M` `deploy/scripts/restore-db.sh`
- `M` `deploy/scripts/smoke.sh`
- `??` `deploy/scripts/verify-backup.sh`
- `MM` `deploy/scripts/vps-discovery.sh`
- `??` `docs/deployment/final-local-validation-report.md`
- `??` `docs/deployment/hostinger-deployment-package.md`
- `??` `docs/deployment/local-stack.md`
- `??` `docs/deployment/native-integration.md`
- `M` `docs/deployment/production-readiness-checklist.md`
- `M` `docs/deployment/production-runbook.md`
- `M` `docs/deployment/staging-plan.md`
- `??` `docs/deployment/update-plan.md`
- `M` `docs/deployment/vps-access-and-discovery.md`
- `M` `docs/integrations/odoo-catalogue-import.md`
- `M` `docs/integrations/odoo-catalogue-variant-model.md`
- `M` `docs/integrations/odoo-import-approval-gate.md`
- `M` `docs/integrations/odoo-import-idempotency.md`
- `??` `docs/integrations/odoo-order-financials.md`
- `M` `eslint.config.js`
- `M` `package-lock.json`
- `M` `package.json`
- `??` `public/og-image.png`
- `??` `src/assets/logo-footer.png`
- `D` `src/assets/logo-footer.png.asset.json`
- `M` `src/components/CartDrawer.tsx`
- `??` `src/components/MinOrderNotice.tsx`
- `M` `src/components/SiteFooter.tsx`
- `M` `src/lib/admin-store.ts`
- `M` `src/lib/catalogue-api.ts`
- `M` `src/lib/store.test.ts`
- `M` `src/lib/store.ts`
- `M` `src/routes/__root.tsx`
- `M` `src/routes/admin.content.tsx`
- `M` `src/routes/cakes.tsx`
- `M` `src/routes/chocolates.tsx`
- `M` `src/routes/cupcakes.tsx`
- `M` `src/routes/customize.tsx`
- `M` `src/routes/delivery.tsx`
- `M` `src/routes/donuts.tsx`
- `M` `src/routes/extras.tsx`
- `M` `src/routes/gifts.tsx`
- `M` `src/routes/payment.tsx`
- `M` `src/routes/shop.tsx`
- `M` `src/routes/track.$id.tsx`
- `??` `tests/`
- `M` `vite.config.ts`

## 9. Recommended commit

Commit every path in section 8, once you've reviewed it:

```
git add -A
git status   # confirm no .env.prod, vps-report or .local-integration
git commit
```

```
Fix variant pricing and close local development

Odoo catalogue sync reduced size-variant prices to the base price
because the importer never wrote price_extra. The importer now
establishes each approved delta in Odoo without overwriting existing
values, and the worker publishes Odoo's own selling price only after
every approved variant reconciles.

Also adds a monitoring alert for refused publications, removes Lovable
hosting references from the HTML, and finalizes the Hostinger
deployment package.
```

## 10. Hostinger execution plan

Each numbered stage ends at a checkpoint. Stop at the first failure. Steps marked **approval** change
shared infrastructure or production data.

1. **Discovery (read-only).** Run `deploy/scripts/vps-discovery.sh` from the hPanel browser terminal,
   as described in [vps-access-and-discovery.md](vps-access-and-discovery.md). Review capacity, ports
   (18010, 18011, 18069), Docker, Caddy, Odoo and PostgreSQL instances, myMakan, Maskan and backups.
   Keep the baseline.
2. **Safety net.** Confirm an hPanel snapshot and backups for myMakan and Maskan. Agree how Docker
   will be accessed.
3. **Place the code (approval).** Commit, then clone to `/opt/terrific-bites` at the approved SHA.
   Create `deploy/.env.prod` with separate `openssl rand -hex 32` secrets, mode 600.
4. **Docker validation.** Build both images, then follow the deployment sequence in
   [hostinger-deployment-package.md](hostinger-deployment-package.md): PostgreSQL and Redis, migrations,
   seed, `odoo-init`, bootstrap, admin user, full stack up. Confirm every container is healthy and
   memory is within limits, and compare myMakan and Maskan against the baseline.
5. **Catalogue import (approval).** Follow "Initial catalogue import". Accept only CLEAN with 55 of 55
   prices. Clear `ODOO_WRITE_APPROVED_TARGET` afterwards.
6. **Check on loopback.** `curl -H 'Host: api.terrific-bites.trunexus.ai' http://127.0.0.1:18010/api/v1/readiness`
   must return 200, and `http://127.0.0.1:18011/` must serve the storefront.
7. **Backups and monitoring.** Run `backup-all.sh prod first` and `verify-backup.sh`, schedule both,
   then `monitor.sh --test-alert` and confirm the alert arrives.
8. **Caddy and API DNS (approval).** Add the `api.terrific-bites` record and both site blocks, run
   `caddy validate`, then reload gracefully. Run `scripts/smoke.sh`, confirm Berry Truffle LARGE BOX
   reads 14.38 through the API, and recheck existing sites against the baseline.
9. **Cutover (approval).** Lower the TTL a day ahead, then repoint `terrific-bites` to `187.127.159.23`.
10. **Production smoke test.** Walk the storefront and Admin in both languages, check the footer logo,
    place one demo order and confirm it's marked `simulated`, and compare myMakan and Maskan against
    the baseline.
11. **Rollback at any point.** Use the rollback table in the deployment package. Keep Lovable serving
    until the VPS has run cleanly for an agreed period.
