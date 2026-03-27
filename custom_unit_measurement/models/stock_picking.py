from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Campo que será True se, entre os movimentos, ao menos um tiver unidade secundária ativa
    has_secondary = fields.Boolean(
        string="Tem Unidade Secundária",
        compute="_compute_has_secondary",
        store=True
    )
    
    @api.depends('move_ids_without_package.x_secondary_active')
    def _compute_has_secondary(self):
        # Para cada picking, verifica se há algum movimento com x_secondary_active = True
        for picking in self:
            picking.has_secondary = any(move.x_secondary_active for move in picking.move_ids_without_package)
    
    
    # Método removido: x_secondary_qty_available agora é calculado automaticamente
    # Não é mais necessário atualizar manualmente na validação do picking
