from odoo import api, fields, models


class PurchaseOrder(models.Model):
    """Inherits the class purchase.order for customizations"""
    _inherit = 'purchase.order'

    purchase_order_for = fields.Selection([
        ('Famù - negozio', 'Famù - negozio'),
        ('Famù - bistrot', 'Famù - bistrot'),
        ('Famù - parco', 'Famù - parco'),
        ('Famù - magazzino centrale', 'Famù - magazzino centrale')
    ])
