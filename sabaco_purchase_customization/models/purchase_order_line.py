from odoo import models, fields

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Campo para UdM acquisto (Unidade de Medida de Compra)
    purchase_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='UdM acquisto',
        help='Unidade de medida utilizada para a compra deste produto.'
    )

    # Campo texto livre para UdM acquisto libera (editável)
    purchase_uom_free = fields.Char(
        string='UdM acquisto libera',
        help='Campo livre para informar uma unidade de medida de compra personalizada.'
    )
