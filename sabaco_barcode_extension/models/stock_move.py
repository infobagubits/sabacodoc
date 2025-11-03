# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    packaging_qty_test = fields.Float(
        string='Test Packaging Qty',
        compute='_compute_packaging_qty_test',
        store=False,
        help='Campo de teste com valor fixo'
    )

    @api.depends('product_id')
    def _compute_packaging_qty_test(self):
        """Campo de teste que retorna sempre 5.00 para validar inserção"""
        for move in self:
            move.packaging_qty_test = 5.00

    def _get_fields_stock_barcode(self):
        """Estende os campos disponíveis no contexto JavaScript do barcode"""
        fields = super()._get_fields_stock_barcode()
        # Adiciona x_studio_confezioni_richieste apenas se o campo existir no modelo
        if 'x_studio_confezioni_richieste' in self._fields and 'x_studio_confezioni_richieste' not in fields:
            fields.append('x_studio_confezioni_richieste')
        return fields

