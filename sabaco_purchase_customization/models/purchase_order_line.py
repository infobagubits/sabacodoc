from odoo import models, fields

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Campo testo libero per UdM acquisto libera (modificabile)
    purchase_uom_free = fields.Char(
        string='UdM acquisto libera',
        help='Campo libero per inserire un\'unità di misura di acquisto personalizzata.'
    )