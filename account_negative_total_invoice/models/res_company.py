from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    allow_negative_total_invoice = fields.Boolean(
        string="Consenti fatture con totale negativo",
        help="Se attivo, le fatture clienti e fornitori possono essere confermate "
             "anche se l'importo totale è negativo.",
    )
