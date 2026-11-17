# Piped into `odoo shell` by the odoo-init step. Safe to run repeatedly.
#
# Prepares a freshly created Odoo database for the catalogue import and order push: company
# currency (SAR, decision D07), the Saudi chart of accounts, 15% VAT included in prices, a SAR
# pricelist, delivery and discount service products, product variants, and one least-privilege
# user per job so that nothing authenticates as the Odoo administrator.
#
# VAT inclusion and delivery tax are proposed rules awaiting client finance approval. See
# docs/integrations/odoo-order-financials.md.
#
#   order sync worker   reads products, creates partners and sale orders
#   catalogue import    one-off CLI that creates products, never a long-running service
import os


def upsert_user(login, password, name, group_xml_ids):
    Users = env["res.users"].with_context(no_reset_password=True)  # noqa: F821
    groups = [env.ref(xml_id).id for xml_id in group_xml_ids]  # noqa: F821
    values = {"name": name, "login": login, "password": password, "group_ids": [(6, 0, groups)]}
    user = Users.search([("login", "=", login)], limit=1)
    if user:
        user.write(values)
    else:
        user = Users.create(values)
    if user.has_group("base.group_system"):
        raise SystemExit(f"{login} must not hold Odoo administrator rights")
    return user


def ensure_saudi_localization(company):
    if company.chart_template == "sa":
        return
    # Replacing a chart of accounts that already has entries would corrupt the books.
    if env["account.move"].search_count([]):  # noqa: F821
        raise SystemExit("This database has accounting entries: load the Saudi chart by hand")
    company.country_id = env.ref("base.sa")  # noqa: F821
    env["account.chart.template"].try_loading("sa", company=company, install_demo=False)  # noqa: F821


def ensure_price_included_vat(company):
    """Storefront prices already contain VAT, so Odoo must extract it, never add it."""
    vat = company.account_sale_tax_id
    if vat.type_tax_use != "sale" or vat.amount != 15:
        raise SystemExit(f"Expected the company's default sale tax to be 15% VAT, got {vat.name!r}")
    if vat.price_include_override != "tax_included":
        vat.price_include_override = "tax_included"
    # Line-by-line rounding would drift from the storefront's single VAT figure.
    company.tax_calculation_rounding_method = "round_globally"
    goods = env["product.template"].search([("type", "=", "consu")])  # noqa: F821
    goods.filtered(lambda p: p.taxes_id != vat).write({"taxes_id": [(6, 0, [vat.id])]})
    return vat


def ensure_pricelist(company, currency):
    Pricelist = env["product.pricelist"]  # noqa: F821
    domain = [("currency_id", "=", currency.id), ("company_id", "in", [company.id, False])]
    return Pricelist.search(domain, limit=1) or Pricelist.create(
        {"name": "Terrific Bites SAR", "currency_id": currency.id, "company_id": company.id}
    )


def ensure_service_product(code, name, vat):
    """Delivery and discount lines. Services, so the catalogue sync never sees them."""
    Template = env["product.template"].with_context(active_test=False)  # noqa: F821
    values = {
        "name": name,
        "default_code": code,
        "type": "service",
        "sale_ok": True,
        "purchase_ok": False,
        "active": True,
        "invoice_policy": "order",
        "taxes_id": [(6, 0, [vat.id])],
    }
    found = Template.search([("default_code", "=", code)], limit=1)
    if found:
        found.write(values)
        return found
    return Template.create(values)


sar = env.ref("base.SAR")  # noqa: F821 - `env` is provided by odoo shell
sar.active = True
company = env.company  # noqa: F821
if company.currency_id != sar and not env["account.move"].search_count([]):  # noqa: F821
    company.currency_id = sar

ensure_saudi_localization(company)
vat = ensure_price_included_vat(company)
pricelist = ensure_pricelist(company, sar)
ensure_service_product("TB-DELIVERY-FEE", "Delivery Fee", vat)
ensure_service_product("TB-PROMO-DISCOUNT", "Promotional Discount", vat)

env["res.config.settings"].create({"group_product_variant": True}).execute()  # noqa: F821

order_sync = upsert_user(
    os.environ["ODOO_ORDER_SYNC_LOGIN"],
    os.environ["ODOO_ORDER_SYNC_PASSWORD"],
    "Terrific Bites Order Sync",
    (
        "base.group_user",
        "base.group_partner_manager",
        "sales_team.group_sale_salesman_all_leads",
    ),
)
catalogue_import = upsert_user(
    os.environ["ODOO_CATALOGUE_IMPORT_LOGIN"],
    os.environ["ODOO_CATALOGUE_IMPORT_PASSWORD"],
    "Terrific Bites Catalogue Import",
    (
        "base.group_user",
        "sales_team.group_sale_manager",
        "product.group_product_manager",
        "terrific_order_sync.group_catalogue_import",
    ),
)

env.cr.commit()  # noqa: F821
print(
    f"odoo bootstrap complete: order_sync={order_sync.id}, "
    f"catalogue_import={catalogue_import.id}, currency={env.company.currency_id.name}, "  # noqa: F821
    f"pricelist={pricelist.name}, vat={vat.name} included"
)
