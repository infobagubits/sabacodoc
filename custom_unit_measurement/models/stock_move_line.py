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
    
    is_uom_weight = fields.Boolean(
        string='UdM Peso',
        compute='_compute_is_uom_weight',
        store=False,
    )

    @api.depends('product_uom_id')
    def _compute_is_uom_weight(self):
        """Retorna True se a UdM da linha contém 'kg' no nome (case-insensitive).
        Usa comparação por nome porque o UoM 'KG' customizado pode estar
        em categoria diferente da categoria padrão de peso do Odoo.
        """
        cr = self.env.cr
        uom_ids = list({line.product_uom_id.id for line in self if line.product_uom_id.id})
        if not uom_ids:
            for line in self:
                line.is_uom_weight = False
            return

        # name é JSONB no Odoo 18 → cast para text antes de LOWER/LIKE
        cr.execute(
            "SELECT id FROM uom_uom "
            "WHERE id = ANY(%s) AND LOWER(name::text) LIKE '%%kg%%'",
            (uom_ids,)
        )
        kg_ids = {r[0] for r in cr.fetchall()}

        for line in self:
            uom_id = line.product_uom_id.id if line.product_uom_id else False
            line.is_uom_weight = bool(uom_id and uom_id in kg_ids)

    product_packaging_id = fields.Many2one(
        'product.packaging',
        string='Confezione',
        domain="[('product_id', '=', product_id)]",
        readonly=False,
    )
    
    product_packaging_qty = fields.Float(
        string='Quantità Confezione',
        readonly=False,
        digits=(16, 10),  # Armazena com 10 decimais para precisão nos cálculos
    )
    
    # Campo para exibição com arredondamento (NÃO armazenado = não causa loops)
    product_packaging_qty_display = fields.Float(
        string='Qtà Confezione',
        compute='_compute_packaging_qty_display',
        digits=(16, 2),  # Exibe com 2 decimais
        store=False,  # IMPORTANTE: não armazenar para evitar loops
    )
    
    @api.depends('product_packaging_qty')
    def _compute_packaging_qty_display(self):
        """Calcula o valor arredondado para exibição."""
        for line in self:
            line.product_packaging_qty_display = line.product_packaging_qty
    
    @api.onchange('quantity', 'product_packaging_id')
    def _onchange_quantity(self):
        """
        Quando altera quantidade total o confezione, calcula automaticamente
        a quantidade de confezioni.
        
        product_packaging_qty = quantity / product_packaging_id.qty
        Mantém exatidão: 192.500 KG ÷ 180 = 1,0694444444 confezioni
        
        NOTA: Questo è l'UNICO onchange per evitare loop infiniti.
        La quantità totale (quantity) NON viene mai calcolata automaticamente
        da product_packaging_qty per prevenire cicli di ricalcolo.
        """
        if self.product_packaging_id and self.quantity and self.product_packaging_id.qty:
            self.product_packaging_qty = self.quantity / self.product_packaging_id.qty
        elif not self.product_packaging_id:
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
        """
        Ao deletar uma linha, atualiza a quantidade secundária do movimento.
        Usa flag de contexto para evitar loop infinito de recomputação.
        """
        # Evita loop: se já estamos atualizando, não dispara novamente
        if self.env.context.get('_skip_secondary_qty_update'):
            return super().unlink()
        
        # Salva referência aos moves ANTES de deletar
        moves_to_update = self.mapped('move_id')
        
        # Deleta os registros
        res = super().unlink()
        
        # Atualiza os moves com flag para evitar loop
        for move in moves_to_update.with_context(_skip_secondary_qty_update=True):
            if move.exists():
                total = sum(move.move_line_ids.mapped('x_secondary_qty'))
                move.with_context(_skip_secondary_qty_update=True).x_secondary_qty = total
        
        return res

    def _update_move_secondary_qty(self):
        """
        Soma as quantidades secundárias das linhas e atualiza a move.
        Usa flag de contexto para evitar loop infinito.
        """
        if self.env.context.get('_skip_secondary_qty_update'):
            return
        
        for line in self:
            if line.move_id:
                total = sum(line.move_id.move_line_ids.mapped('x_secondary_qty'))
                line.move_id.with_context(_skip_secondary_qty_update=True).x_secondary_qty = total