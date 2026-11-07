# Production readiness checklist

Tracks what has to be true at each stage. An item is only ticked when it has been tested in
that environment. Passing locally doesn't count for staging or production.

## Stage design

| Setting | Stage A: client demo | Stage B: production |
|---|---|---|
| `DEPLOYMENT_STAGE` (backend) | `demo` | `live` |
| `VITE_DEMO_MODE` (frontend) | `true` | `false` |
| Payment, notification, Odoo order push | Must all be `stub`; the app refuses to start otherwise | Must all be real; the app refuses to start otherwise |
| New orders | `DEMO-` number, `is_demo=true` | `TB-` number, `is_demo=false` |
| Odoo sync status | `simulated` | `synced`, with an Odoo sale order id |

Moving to Stage B adds to this design and doesn't replace it. Payment, notification and Odoo
providers already sit behind adapters, so real ones plug in without changing checkout or the
outbox. Demo orders stay permanently out of Odoo through their `is_demo` flag, even on the same
database, though Stage B should still start on a fresh one.

## Stage A: client demonstration

**Application (tested locally)**
- [x] Demo banner on every page, in English and Arabic
- [x] Payment page has no card fields and says it's a demo payment
- [x] Sign-in and signup say they're a demo
- [x] Orders are labelled `DEMO-` and carry a demo notice on success, tracking and the PDF
- [x] Demo orders never reach the Odoo pusher, even with the live pusher selected
- [x] Admin shows "simulated (not in Odoo)"
- [x] Tracking tokens are random
- [x] Unsafe production settings stop the app from starting
- [x] Admin saves work across the two hostnames

**Infrastructure (not started)**
- [ ] VPS access confirmed and discovery report reviewed
- [ ] Capacity confirmed, including the effect on myMakan and Maskan
- [ ] Staging plan approved and all steps passed
- [ ] Docker image and Compose stack tested on the VPS
- [ ] Backup and restore tested on the VPS
- [ ] HTTPS working through Caddy, with existing sites unaffected
- [ ] Alert webhook set up and a real alert received
- [ ] External uptime check on `/api/v1/health` (the VPS can't report its own outage)
- [ ] Page timing measured on the VPS and on Lovable's hosting
- [ ] Lovable builds the correct branch with the production API URL
- [ ] Demo admin account created with a unique password
- [ ] Demo database holds no real customer data

**Sign-off**
- [ ] Client told in writing that this is a demo, with what isn't real

## Stage B: production release

**Blockers: not built**
- [ ] Real payment provider, including webhooks, refunds and failure handling
- [ ] `POST /orders/{id}/pay` confirmed by the provider, not by the browser. Today anyone with an order id can mark it paid
- [ ] Real customer accounts on the server, with verified sign-in and password reset
- [ ] Orders tied to the signed-in customer, with access checks on order lookups
- [ ] Real notification provider (email/SMS)
- [ ] Off-site, encrypted backups, with a restore test
- [ ] Live Odoo order push tested against a sandbox, then production, with explicit approval
- [ ] Production Odoo instance decided, along with how the VPS reaches it
- [ ] Catalogue sourced from production Odoo, not the seed files

**Blockers: content and compliance**
- [ ] Remove seeded reviews. They show made-up customers as verified buyers
- [ ] Replace placeholder copy (the About page has lorem ipsum) and placeholder staff in the admin store
- [ ] Privacy policy and terms, and a data-retention decision for customer details
- [ ] Legal and tax review of prices and receipts (the current PDF isn't a tax invoice)
- [ ] Payment card compliance scope agreed with the provider

**Security**
- [ ] Rate limits on order creation, tracking lookup and customer sign-in
- [ ] Independent security review
- [ ] Repository made private. It's currently publicly readable
- [ ] Secrets rotated, and a secret manager decided on
- [ ] Removal of client-side admin stores where the backend now owns the data

**Operations**
- [ ] Alerts routed to a named person, with an on-call plan
- [ ] Log retention and error tracking
- [ ] Load test at expected peak
- [ ] Decision on whether a shared VPS is still acceptable. The architecture docs expect managed PostgreSQL and Redis with point-in-time recovery
- [ ] Rollback rehearsed
- [ ] Fresh production database, with no demo orders carried over

**Before go-live**
- [ ] Set `DEPLOYMENT_STAGE=live` and `VITE_DEMO_MODE=false`
- [ ] Confirm a real low-value payment and refund end to end
- [ ] Confirm one real order reaches Odoo with a sale order id, and shows `synced`
- [ ] Business sign-off

## Decisions to reconcile

- **D20 means two different things.** In `data/catalogue/catalogue-decisions.json` it's the
  Odoo external-id strategy. In `data/catalogue/catalogue-business-approvals.json` it's the
  attribute and variant write approval. The approval status has not been changed.
- **The approval evidence covers `terrific_dev` only.** Run `--validate` and `--plan` against
  production Odoo and review them again before any variant write there.
- **`docs/integrations/odoo-catalogue-import.md` is out of date.** It still says D03, D04, D08,
  D10, D19 and D20 are `PROPOSED`, but the approvals file records them as `APPROVED`.
