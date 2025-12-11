from odoo import models, fields


class Listino(models.Model):
    _name = 'res.partner.listino'
    _description = 'Listino Consegnato'
    _order = 'name'

    name = fields.Char(string='Nome', required=True)
    active = fields.Boolean(default=True)

