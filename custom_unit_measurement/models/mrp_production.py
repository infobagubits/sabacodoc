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

    def _apply_secondary_qty_to_move_lines(self, move, secondary_qty):
        """Distribui a quantità secondaria sulle stock.move.line in proporzione a quantity."""
        lines = move.move_line_ids
        if not lines or not secondary_qty:
            return
        total_ml_qty = sum(lines.mapped('quantity'))
        for move_line in lines:
            if total_ml_qty and move_line.quantity:
                line_sec = secondary_qty * (move_line.quantity / total_ml_qty)
            elif len(lines) == 1:
                line_sec = secondary_qty
            else:
                line_sec = secondary_qty / len(lines)
            vals = {'x_secondary_qty': line_sec}
            if hasattr(move_line, 'x_studio_quantita_secondaria'):
                vals['x_studio_quantita_secondaria'] = line_sec
            move_line.with_context(_skip_secondary_qty_update=True).write(vals)

    def button_mark_done(self):
        """
        Estende o método de finalização da produção para gerenciar
        a quantidade secundária do produto acabado e dos componentes consumidos.
        """
        res = super().button_mark_done()

        for production in self:
            _logger.info(
                f"=== PRODUÇÃO {production.name}: quantidade secundária (acabado + componentes) ==="
            )

            # --- Produto acabado ---
            if production.product_id.x_secondary_uom_id:
                finished_moves = production.move_finished_ids.filtered(
                    lambda m: m.product_id == production.product_id and m.state == 'done'
                )
                if finished_moves:
                    if production.product_packaging_qty:
                        secondary_qty = production.product_packaging_qty
                        _logger.info(f"Acabado: product_packaging_qty = {secondary_qty}")
                    else:
                        secondary_qty = production.product_qty
                        _logger.info(f"Acabado: product_qty (1:1) = {secondary_qty}")

                    for move in finished_moves:
                        _logger.info(
                            f"Acabado move {move.id}: x_secondary_qty = {secondary_qty}"
                        )
                        move.write({'x_secondary_qty': secondary_qty})
                        production._apply_secondary_qty_to_move_lines(move, secondary_qty)

                    _logger.info(
                        f"✅ {production.name}: acabado {secondary_qty} "
                        f"{production.product_id.x_secondary_uom_id.name}"
                    )
                else:
                    _logger.warning(
                        f"Nenhum move finalizado para produto acabado em {production.name}"
                    )

            # --- Componentes (consumo, movimenti negativi) ---
            raw_moves = production.move_raw_ids.filtered(
                lambda m: m.state == 'done' and m.product_id.x_secondary_uom_id
            )
            for move in raw_moves:
                secondary_qty = move.x_secondary_qty or 0.0
                if not secondary_qty and move.product_uom_id == move.product_id.x_secondary_uom_id:
                    secondary_qty = move.quantity
                    _logger.info(
                        f"Componente move {move.id}: UoM = UdM sec., uso quantity = {secondary_qty}"
                    )
                if not secondary_qty:
                    _logger.info(
                        f"Componente move {move.id}: x_secondary_qty vuoto, skip (compilare in OP)"
                    )
                    continue
                _logger.info(
                    f"Componente move {move.id}: x_secondary_qty = {secondary_qty} → move lines"
                )
                move.write({'x_secondary_qty': secondary_qty})
                production._apply_secondary_qty_to_move_lines(move, secondary_qty)

        return res
