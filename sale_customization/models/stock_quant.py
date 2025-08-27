from odoo import models, fields, api

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    x_secondary_uom_id = fields.Many2one(
        related='product_id.product_tmpl_id.x_secondary_uom_id',
        comodel_name='uom.uom',
        string='Unità Secondaria',
        store=False,
        readonly=True
    )

    x_secondary_qty = fields.Float(
        string="Qtà Secondaria",
        compute="_compute_secondary_qty",
        store=False
    )

    @api.depends('product_id', 'lot_id', 'location_id')
    def _compute_secondary_qty(self):
        for quant in self:
            prodotto = quant.product_id
            lotto = quant.lot_id
            ubicazione = quant.location_id

            totale_secondario = 0.0

            # Cercare tutte le righe di movimento correlate
            righe = self.env['stock.move.line'].search([
                ('product_id', '=', prodotto.id),
                ('lot_id', '=', lotto.id),
                ('state', '=', 'done'),
                '|',
                    ('location_id', '=', ubicazione.id),
                    ('location_dest_id', '=', ubicazione.id),
            ])

            # Calcolare totale considerando i valori in stock.move.line
            for riga in righe:
                if not riga.x_secondary_qty:
                    continue

                if riga.location_dest_id.id == ubicazione.id:
                    totale_secondario += riga.x_secondary_qty  # Entrata
                elif riga.location_id.id == ubicazione.id:
                    totale_secondario -= riga.x_secondary_qty  # Uscita

            quant.x_secondary_qty = totale_secondario
