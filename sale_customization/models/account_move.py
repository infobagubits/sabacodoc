from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    zero_amount_line_warning = fields.Char(
        string="Avviso importo zero",
        compute='_compute_zero_amount_line_warning',
        store=False,
    )

    @api.depends('invoice_line_ids', 'invoice_line_ids.price_subtotal', 'invoice_line_ids.product_id', 'move_type')
    def _compute_zero_amount_line_warning(self):
        """
        Calcola se esistono righe con importo 0 e restituisce il messaggio di avviso.
        Mostra avviso per QUALSIASI riga prodotto con price_subtotal = 0 (solo fatture/ricevute).
        """
        for move in self:
            move.zero_amount_line_warning = False

            if move.move_type not in (
                'out_invoice', 'out_refund', 'in_invoice', 'in_refund',
                'out_receipt', 'in_receipt',
            ):
                continue

            zero_lines = move.invoice_line_ids.filtered(
                lambda l: l.display_type not in ('line_section', 'line_note')
                and l.product_id
                and l.price_subtotal == 0
            )

            if zero_lines:
                product_names = ', '.join(zero_lines.mapped('product_id.name')[:5])
                if len(zero_lines) > 5:
                    product_names += f' (+{len(zero_lines) - 5} altri)'

                move.zero_amount_line_warning = _(
                    'Attenzione! Ci sono %(count)s prodotti con importo 0: %(products)s'
                ) % {
                    'count': len(zero_lines),
                    'products': product_names,
                }
