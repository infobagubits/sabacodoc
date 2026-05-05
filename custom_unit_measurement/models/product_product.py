from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    # Espone i campi del template anche sulle varianti per evitare errori di view/azione.
    x_secondary_uom_id = fields.Many2one(
        related="product_tmpl_id.x_secondary_uom_id",
        readonly=True,
    )
    x_secondary_qty_available = fields.Float(
        related="product_tmpl_id.x_secondary_qty_available",
        readonly=True,
    )
    x_secondary_qty_display = fields.Char(
        related="product_tmpl_id.x_secondary_qty_display",
        readonly=True,
    )

    def action_dummy_secondary_qty(self):
        return True

