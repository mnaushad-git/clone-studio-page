from odoo import fields, models

# The storefront's stable key for each record the catalogue import creates. As with
# sale.order.tb_order_key, a UNIQUE index is what makes the import safe to repeat: a create
# that timed out but committed anyway can be found again by key and adopted, and one still in
# flight can't commit a second copy.
MESSAGE = "This catalogue record has already been imported."


class ProductCategory(models.Model):
    _inherit = "product.category"

    tb_import_key = fields.Char(string="Storefront Import Key", copy=False, readonly=True)
    _tb_import_key_unique = models.Constraint("UNIQUE (tb_import_key)", MESSAGE)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    tb_import_key = fields.Char(string="Storefront Import Key", copy=False, readonly=True)
    _tb_import_key_unique = models.Constraint("UNIQUE (tb_import_key)", MESSAGE)


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    tb_import_key = fields.Char(string="Storefront Import Key", copy=False, readonly=True)
    _tb_import_key_unique = models.Constraint("UNIQUE (tb_import_key)", MESSAGE)


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    tb_import_key = fields.Char(string="Storefront Import Key", copy=False, readonly=True)
    _tb_import_key_unique = models.Constraint("UNIQUE (tb_import_key)", MESSAGE)
