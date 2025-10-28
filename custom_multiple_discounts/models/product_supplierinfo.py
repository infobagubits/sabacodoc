from odoo import models, fields

class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    discount1 = fields.Float(string="Sc. 1%", default=0.0)
    discount2 = fields.Float(string="Sc. 2%", default=0.0)
    discount3 = fields.Float(string="Sc. 3%", default=0.0)

