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
    
    product_packaging_id = fields.Many2one(
        'product.packaging',
        string='Confezione',
        domain="[('product_id', '=', product_id)]",
        readonly=False,
    )
    
    product_packaging_qty = fields.Float(
        string='Quantità Confezione',
        readonly=False,
        digits=(16, 10),  # Consente fino a 10 cifre decimali per mantenere la precisione esatta del valore
    )
    
    @api.onchange('product_packaging_id', 'product_packaging_qty')
    def _onchange_packaging_qty(self):
        """
        Quando altera quantidade de confezioni, calcula a quantidade total.
        quantity = product_packaging_qty * product_packaging_id.qty
        """
        if self.product_packaging_id and self.product_packaging_qty:
            self.quantity = self.product_packaging_qty * self.product_packaging_id.qty
        elif not self.product_packaging_id:
            # Se não c'è confezione, resetta a 0
            self.quantity = 0.0
    
    @api.onchange('quantity', 'product_packaging_id')
    def _onchange_quantity(self):
        """
        Quando altera quantidade total, calcula automaticamente a quantidade de confezioni.
        product_packaging_qty = quantity / product_packaging_id.qty
        Mantém exatidão: 192.500 KG ÷ 180 = 1,0694444444 confezioni
        """
        if self.product_packaging_id and self.quantity:
            # Calcula a quantidade de confezioni dividindo quantidade total pela quantidade por confezione
            self.product_packaging_qty = self.quantity / self.product_packaging_id.qty
        elif not self.product_packaging_id:
            # Se não c'è confezione, resetta a 0
            self.product_packaging_qty = 0.0
    
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