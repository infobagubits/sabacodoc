from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    iva_differita_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Imposta IVA differita (-)',
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
        help="Imposta di acquisto da applicare alle righe della fattura "
             "(registrazione originale) al posto di questa, quando la "
             "fattura è marcata come IVA differita.",
    )
    iva_differita_tax_plus_id = fields.Many2one(
        comodel_name='account.tax',
        string='Imposta IVA differita (+)',
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
        help="Imposta di acquisto da applicare nella registrazione di IVA "
             "differita (storno) al posto di questa.",
    )

    def _get_iva_differita_mapped_taxes(self, plus=False):
        """Per ogni imposta nel recordset, restituisce la sua imposta
        differita se configurata, altrimenti l'imposta stessa.

        Con `plus=False` usa `iva_differita_tax_id` (registrazione
        originale), con `plus=True` usa `iva_differita_tax_plus_id`
        (registrazione di IVA differita)."""
        fname = 'iva_differita_tax_plus_id' if plus else 'iva_differita_tax_id'
        return self.env['account.tax'].union(
            *[tax[fname] or tax for tax in self]
        )
