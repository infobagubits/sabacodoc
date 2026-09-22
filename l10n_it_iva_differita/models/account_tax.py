from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    iva_differita_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Imposta IVA differita',
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
        help="Imposta di acquisto da applicare alle righe della fattura al "
             "posto di questa, quando la fattura è marcata come IVA "
             "differita.",
    )

    def _get_iva_differita_mapped_taxes(self):
        """Per ogni imposta nel recordset, restituisce la sua
        `iva_differita_tax_id` se configurata, altrimenti l'imposta stessa."""
        return self.env['account.tax'].union(
            *[tax.iva_differita_tax_id or tax for tax in self]
        )
