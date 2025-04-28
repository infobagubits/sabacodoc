from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean(string="E' un cliente")
    is_supplier = fields.Boolean(string="E' un fornitore")
