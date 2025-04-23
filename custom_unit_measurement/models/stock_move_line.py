from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    x_secondary_qty = fields.Float(
        string='Quantità Secondaria'
    )

    x_secondary_uom_id = fields.Many2one(
        related='product_id.product_tmpl_id.x_secondary_uom_id',
        comodel_name='uom.uom',
        string='U.M. Secondaria',
        readonly=True,
        store=False,
    )
    
    @api.model
    def create(self, vals):
        """
        Copia o valor da move na primeira linha criada.
        """
        if 'x_secondary_qty' not in vals and 'move_id' in vals:
            move = self.env['stock.move'].browse(vals['move_id'])
            if move and not move.move_line_ids:
                vals['x_secondary_qty'] = move.x_secondary_qty

        res = super().create(vals)
        res._update_move_secondary_qty()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'x_secondary_qty' in vals:
            self._update_move_secondary_qty()
        return res

    def unlink(self):
        moves = self.mapped('move_id')
        res = super().unlink()
        for move in moves:
            move.x_secondary_qty = sum(move.move_line_ids.mapped('x_secondary_qty'))
        return res

    def _update_move_secondary_qty(self):
        """
        Soma as quantidades secundárias das linhas e atualiza a move.
        """
        for line in self:
            if line.move_id:
                total = sum(line.move_id.move_line_ids.mapped('x_secondary_qty'))
                line.move_id.x_secondary_qty = total