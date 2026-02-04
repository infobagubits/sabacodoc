from odoo import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    # Campo helper para o domain
    product_variant_ids = fields.Many2many(
        'product.product',
        compute='_compute_product_variant_ids',
        store=False
    )

    product_packaging_id = fields.Many2one(
        'product.packaging',
        string='Confezione',
        domain="[('product_id', 'in', product_variant_ids)]",
        help='Selezionare la confezione del prodotto da produrre'
    )
    
    product_packaging_qty = fields.Float(
        string='Qtà Confezioni',
        digits=(16, 10),  # Alta precisione per calcoli
        help='Quantità di confezioni da produrre'
    )

    @api.depends('product_id')
    def _compute_product_variant_ids(self):
        """
        Calcula os IDs das variantes de produto para usar no domain.
        """
        for production in self:
            if production.product_id:
                production.product_variant_ids = production.product_id
            else:
                production.product_variant_ids = False

    @api.onchange('product_packaging_id', 'product_packaging_qty')
    def _onchange_product_packaging(self):
        """
        Calcola automaticamente la quantità totale (product_qty) 
        basandosi sulla confezione selezionata e la quantità di confezioni.
        
        Formula: product_qty = product_packaging_qty × product_packaging_id.qty
        """
        if self.product_packaging_id and self.product_packaging_qty:
            if self.product_packaging_id.qty > 0:
                # Calcula a quantidade total
                self.product_qty = self.product_packaging_qty * self.product_packaging_id.qty
        elif not self.product_packaging_id:
            # Se não há confezione selecionada, limpa a quantidade de confezioni
            self.product_packaging_qty = 0.0
