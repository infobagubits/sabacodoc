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
            produto = quant.product_id
            lote = quant.lot_id
            local = quant.location_id

            total_secundario = 0.0

            # Buscar todas as linhas de movimento relacionadas
            linhas = self.env['stock.move.line'].search([
                ('product_id', '=', produto.id),
                ('lot_id', '=', lote.id),
                ('state', '=', 'done'),
                '|',
                    ('location_id', '=', local.id),
                    ('location_dest_id', '=', local.id),
            ])

            # Calcular total considerando os valores em stock.move.line
            for linha in linhas:
                if not linha.x_secondary_qty:
                    continue

                if linha.location_dest_id.id == local.id:
                    total_secundario += linha.x_secondary_qty  # Entrada
                elif linha.location_id.id == local.id:
                    total_secundario -= linha.x_secondary_qty  # Saída

            quant.x_secondary_qty = total_secundario
