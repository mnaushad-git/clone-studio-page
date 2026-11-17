from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # The storefront's order number. A UNIQUE index in PostgreSQL is what makes order creation
    # idempotent: of any number of concurrent or repeated creates with one key, exactly one
    # can commit. client_order_ref can't serve here because staff can edit it freely.
    tb_order_key = fields.Char(
        string="Storefront Order Key",
        copy=False,
        readonly=True,
        help="Set once by the storefront order sync. Guarantees one sale order per order.",
    )

    _tb_order_key_unique = models.Constraint(
        "UNIQUE (tb_order_key)",
        "A sale order already exists for this storefront order.",
    )

    def write(self, vals):
        if "tb_order_key" in vals and any(
            order.tb_order_key and order.tb_order_key != vals["tb_order_key"] for order in self
        ):
            raise UserError(_("The storefront order key cannot be changed once set."))
        return super().write(vals)
