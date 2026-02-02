from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    # Quantidade secundária a ser descartada (entrada manual)
    x_secondary_qty = fields.Float(
        string='Quantità Secondaria',
        help='Quantità secondaria da scartare'
    )

    # Unidade de medida secundária (relacionada do produto)
    x_secondary_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='U.M. Secondaria',
        compute='_compute_secondary_uom_id',
        store=False,
        readonly=True
    )

    @api.depends('product_id')
    def _compute_secondary_uom_id(self):
        """Obtém a UdM secundária do produto selecionado."""
        for scrap in self:
            if scrap.product_id and scrap.product_id.product_tmpl_id.x_secondary_uom_id:
                scrap.x_secondary_uom_id = scrap.product_id.product_tmpl_id.x_secondary_uom_id
            else:
                scrap.x_secondary_uom_id = False

    def do_scrap(self):
        """
        Estende o método de scarto para:
        1. Definir x_secondary_qty no movimento e linhas de movimento criados
        2. Atualizar a quantidade secundária disponível do produto
        """
        # Salva a quantidade secundária ANTES de chamar super()
        # porque precisamos aplicá-la ao movimento criado
        secondary_qty_by_scrap = {scrap.id: scrap.x_secondary_qty for scrap in self}
        
        _logger.info(f"SCRAP do_scrap: secondary_qty_by_scrap = {secondary_qty_by_scrap}")
        
        res = super().do_scrap()
        
        # Após o scarto, atualiza o movimento criado e a quantidade secundária do produto
        for scrap in self:
            secondary_qty = secondary_qty_by_scrap.get(scrap.id, 0.0)
            
            _logger.info(f"SCRAP do_scrap: Processando scrap {scrap.name}, secondary_qty = {secondary_qty}")
            
            # Atualiza o movimento criado com a quantidade secundária
            if scrap.move_ids and secondary_qty:
                for move in scrap.move_ids:
                    _logger.info(f"SCRAP do_scrap: Atualizando move {move.id} com x_secondary_qty = {secondary_qty}")
                    move.write({'x_secondary_qty': secondary_qty})
                    
                    # Atualiza também as linhas de movimento
                    for line in move.move_line_ids:
                        _logger.info(f"SCRAP do_scrap: Atualizando move_line {line.id} com x_secondary_qty = {secondary_qty}")
                        line.with_context(_skip_secondary_qty_update=True).write({'x_secondary_qty': secondary_qty})
            
            # Subtrai a quantidade secundária do estoque disponível do produto
            if secondary_qty and scrap.product_id:
                template = scrap.product_id.product_tmpl_id
                uom = template.x_secondary_uom_id
                
                if template and uom:
                    template.x_secondary_qty_available -= secondary_qty
                    _logger.info(
                        f"Scarto: Subtraído {secondary_qty} {uom.name} do produto {scrap.product_id.name}. "
                        f"Novo total secundário: {template.x_secondary_qty_available}"
                    )
        
        return res
