"""Read-only repositories over specific Odoo models.

Each repository wraps app.integrations.odoo.client.OdooClient with model-specific
knowledge (which fields to request, sane pagination bounds) so discovery/ and the CLI
scripts never build raw Odoo domains/field lists themselves. Every repository method
is read-only by construction — it only ever calls OdooClient's read-only surface.
"""

from __future__ import annotations
