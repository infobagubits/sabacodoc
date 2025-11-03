# -*- coding: utf-8 -*-

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_fields_stock_barcode(self):
        """Estende os campos disponíveis no contexto JavaScript do barcode"""
        fields = super()._get_fields_stock_barcode()
        # Adiciona product_packaging_qty se ainda não estiver na lista
        if 'product_packaging_qty' not in fields:
            fields.append('product_packaging_qty')
        return fields

