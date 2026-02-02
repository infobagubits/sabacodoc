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

    def _prepare_move_values(self):
        """Estende os valores do movimento para incluir a quantidade secundária."""
        vals = super()._prepare_move_values()
        
        _logger.info(f"SCRAP _prepare_move_values: x_secondary_qty = {self.x_secondary_qty}")
        
        # SEMPRE adiciona a quantidade secundária ao movimento (mesmo se for 0)
        vals['x_secondary_qty'] = self.x_secondary_qty or 0.0
        
        # Modifica a move_line para incluir x_secondary_qty
        if vals.get('move_line_ids'):
            new_move_line_ids = []
            for line_vals in vals['move_line_ids']:
                if isinstance(line_vals, tuple) and len(line_vals) == 3:
                    # Cria nova tupla com o dicionário atualizado
                    line_dict = dict(line_vals[2])  # Copia o dicionário
                    line_dict['x_secondary_qty'] = self.x_secondary_qty or 0.0
                    new_move_line_ids.append((line_vals[0], line_vals[1], line_dict))
                else:
                    new_move_line_ids.append(line_vals)
            vals['move_line_ids'] = new_move_line_ids
            
        _logger.info(f"SCRAP _prepare_move_values: vals = {vals}")
        
        return vals

    def do_scrap(self):
        """Estende o método de scarto para atualizar a quantidade secundária disponível."""
        _logger.info(f"SCRAP do_scrap: Iniciando scarto para {self.name}, x_secondary_qty = {self.x_secondary_qty}")
        
        res = super().do_scrap()
        
        # Após o scarto, subtrai a quantidade secundária do estoque disponível do produto
        for scrap in self:
            if scrap.x_secondary_qty and scrap.product_id:
                template = scrap.product_id.product_tmpl_id
                uom = template.x_secondary_uom_id
                
                if template and uom:
                    template.x_secondary_qty_available -= scrap.x_secondary_qty
                    _logger.info(
                        f"Scarto: Subtraído {scrap.x_secondary_qty} {uom.name} do produto {scrap.product_id.name}. "
                        f"Novo total secundário: {template.x_secondary_qty_available}"
                    )
        
        return res
