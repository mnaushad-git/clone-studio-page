"""Admin Portal service layer — business logic for auth, orders, products, promo
codes, delivery configuration, and audit logging. Endpoints stay thin; repositories
own raw queries (CLAUDE.md rule 6)."""

from __future__ import annotations
