from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # Da configurare sulla tassa IVA DIFFERITA (es. "IVA differita 22%"):
    # punta alla tassa originale (es. "IVA 22%") che questa sostituisce in
    # fattura. Usata per ricostruire, nella registrazione di storno, il
    # "giro" dalla tassa differita a quella originale.
    iva_differita_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string='Imposta originale (-)',
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
        help="Imposta di acquisto originale (es. IVA 22%) sostituita in "
             "fattura da questa tassa IVA differita. Da configurare sulla "
             "tassa IVA differita, non su quella originale. Necessaria per "
             "generare la registrazione di storno IVA differita.",
    )
    # Da configurare anch'essa sulla tassa IVA DIFFERITA (stessa tassa del
    # campo "Imposta originale (-)"): tassa da usare, al posto di quella
    # presente in fattura, sulla riga Avere dell'imponibile nella
    # registrazione di storno.
    iva_differita_tax_plus_id = fields.Many2one(
        comodel_name='account.tax',
        string='Imposta differita (+)',
        domain="[('type_tax_use', '=', 'purchase'), ('company_id', '=', company_id)]",
        help="Imposta da usare al posto di questa sulla riga Avere "
             "dell'imponibile della registrazione di storno IVA differita. "
             "Se non configurata, viene usata questa stessa tassa.",
    )

    def _get_iva_differita_plus_taxes(self):
        """Per ogni tassa differita nel recordset, restituisce la sua
        `iva_differita_tax_plus_id` se configurata, altrimenti la tassa
        stessa."""
        return self.env['account.tax'].union(
            *[tax.iva_differita_tax_plus_id or tax for tax in self]
        )

    def _get_tax_repartition_lines(self, move_type, repartition_type):
        """Righe di ripartizione (fatture o note di credito a seconda di
        `move_type`) di tipo `repartition_type` ('base' o 'tax') per ogni
        tassa nel recordset."""
        self.ensure_one()
        is_refund = move_type in ('in_refund', 'out_refund')
        field_name = 'refund_repartition_line_ids' if is_refund else 'invoice_repartition_line_ids'
        return self[field_name].filtered(lambda r: r.repartition_type == repartition_type)

    def _get_matching_tax_repartition_line(self, move_type, differita_repartition_line):
        """Tra le righe di ripartizione imposta di `self` (tassa originale),
        restituisce quella con la stessa `factor_percent` della riga di
        ripartizione della tassa differita passata (per gestire casi con più
        righe di ripartizione, es. IVA parzialmente indetraibile). Se non
        trova una corrispondenza esatta, restituisce la prima disponibile.
        """
        self.ensure_one()
        rep_lines = self._get_tax_repartition_lines(move_type, 'tax')
        match = rep_lines.filtered(
            lambda r: abs(r.factor_percent - differita_repartition_line.factor_percent) < 0.01
        )
        return match[:1] or rep_lines[:1]
