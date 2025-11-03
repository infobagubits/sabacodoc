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

