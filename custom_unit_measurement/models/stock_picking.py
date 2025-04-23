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
    
    
    def button_validate(self):
        res = super().button_validate()

        for picking in self:
            _logger.info(f"✔ Validando picking ID {picking.id}, tipo: {picking.picking_type_code}")
            for move in picking.move_ids_without_package:
                product = move.product_id
                qty = move.x_secondary_qty
                template = product.product_tmpl_id
                uom = template.x_secondary_uom_id

                _logger.info(f"Produto: {product.name}, Qtd Secundária: {qty}, U.M.: {uom.name if uom else '-'}")

                if not template or not uom:
                    _logger.warning("⚠ Produto sem unidade secundária, ignorado.")
                    continue

                if picking.picking_type_code == 'incoming':
                    template.x_secondary_qty_available += qty
                    _logger.info(f"Somou {qty} → Novo total: {template.x_secondary_qty_available}")

                elif picking.picking_type_code == 'outgoing':
                    template.x_secondary_qty_available -= qty
                    _logger.info(f"Subtraiu {qty} → Novo total: {template.x_secondary_qty_available}")

        return res
