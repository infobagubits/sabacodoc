# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_it_rc_self_invoice_tax_id = fields.Many2one(
        comodel_name="account.tax",
        string="Imposta autofattura (reverse charge)",
        help="Imposta di vendita da applicare nella riga dell'autofattura "
             "generata dal reverse charge, in corrispondenza di questa imposta "
             "di acquisto. Deve essere un'imposta con un'unica ripartizione "
             "positiva verso il conto IVA a debito (registro vendite).",
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]",
    )
