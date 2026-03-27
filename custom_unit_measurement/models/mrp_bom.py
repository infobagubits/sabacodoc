from odoo import models, fields, api


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

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
        help='Selezionare la confezione del prodotto'
    )
    
    product_packaging_qty = fields.Float(
        string='Qtà Confezioni',
        digits=(16, 10),  # Alta precisione per calcoli
        help='Quantità di confezioni da produrre'
    )

    @api.depends('product_id', 'product_tmpl_id')
    def _compute_product_variant_ids(self):
        """
        Calcula os IDs das variantes de produto para usar no domain.
        Retorna a variante específica se existir, senão todas as variantes do template.
        """
        for bom in self:
            if bom.product_id:
                # Se há variante específica, usa ela
                bom.product_variant_ids = bom.product_id
            elif bom.product_tmpl_id:
                # Se há apenas template, usa todas as variantes
                bom.product_variant_ids = bom.product_tmpl_id.product_variant_ids
            else:
                # Caso vazio
                bom.product_variant_ids = False

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
