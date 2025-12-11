from odoo import models, fields


class ContactMethod(models.Model):
    _name = 'res.partner.contact.method'
    _description = 'Metodo di Contatto'
    _order = 'name'

    name = fields.Char(string='Nome', required=True)
    active = fields.Boolean(default=True)

