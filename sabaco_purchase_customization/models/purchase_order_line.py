from odoo import models, fields

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Campo texto livre para UdM acquisto libera (editável)
    purchase_uom_free = fields.Char(
        string='UdM acquisto libera',
        help='Campo livre para informar uma unidade de medida de compra personalizada.'
    )
