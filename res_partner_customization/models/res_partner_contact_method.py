from odoo import models, fields

class ContactMethod(models.Model):
    _name = 'res.partner.contact_method'
    _description = 'Metodo di Contatto'

    name = fields.Char(string='Nome', required=True)