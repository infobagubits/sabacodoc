from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


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

    def button_mark_done(self):
        """
        Estende o método de finalização da produção para gerenciar
        a quantidade secundária do produto acabado.
        """
        # Chama o método original do Odoo (produz normalmente)
        res = super().button_mark_done()
        
        # Processa cada ordem de produção
        for production in self:
            _logger.info(f"=== PRODUÇÃO {production.name}: Iniciando processamento de quantidade secundária ===")
            
            # Verifica se o produto tem unidade secundária configurada
            if not production.product_id.x_secondary_uom_id:
                _logger.info(f"Produto {production.product_id.name} não tem unidade secundária. Pulando.")
                continue
            
            # Pega os movimentos do produto acabado (finished product)
            finished_moves = production.move_finished_ids.filtered(
                lambda m: m.product_id == production.product_id and m.state == 'done'
            )
            
            if not finished_moves:
                _logger.warning(f"Nenhum movimento finalizado encontrado para {production.product_id.name}")
                continue
            
            # Calcula a quantidade secundária
            secondary_qty = 0.0
            
            # Cenário 1: Se tem quantidade de confezioni informada, usa ela
            if production.product_packaging_qty:
                secondary_qty = production.product_packaging_qty
                _logger.info(f"Usando product_packaging_qty: {secondary_qty}")
            
            # Cenário 2: Se não tem packaging, usa a quantidade produzida (1:1)
            else:
                secondary_qty = production.product_qty
                _logger.info(f"Usando product_qty (1:1): {secondary_qty}")
            
            # Atualiza os movimentos com a quantidade secundária
            for move in finished_moves:
                _logger.info(f"Atualizando stock.move ID {move.id} com x_secondary_qty = {secondary_qty}")
                move.write({'x_secondary_qty': secondary_qty})
                
                # Atualiza também as linhas de movimento detalhadas
                for move_line in move.move_line_ids:
                    _logger.info(f"Atualizando stock.move.line ID {move_line.id} com x_secondary_qty = {secondary_qty}")
                    
                    # Escreve em ambos os campos (customizado e Studio, se existir)
                    vals = {'x_secondary_qty': secondary_qty}
                    if hasattr(move_line, 'x_studio_quantita_secondaria'):
                        vals['x_studio_quantita_secondaria'] = secondary_qty
                    
                    move_line.with_context(_skip_secondary_qty_update=True).write(vals)
            
            _logger.info(
                f"✅ Produção {production.name}: Quantidade secundária {secondary_qty} "
                f"{production.product_id.x_secondary_uom_id.name} registrada com sucesso!"
            )
        
        return res
