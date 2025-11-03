# -*- coding: utf-8 -*-

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_fields_stock_barcode(self):
        """Estende os campos disponíveis no contexto JavaScript do barcode"""
        fields = super()._get_fields_stock_barcode()
        # Adiciona x_studio_confezioni_richieste se ainda não estiver na lista
        if 'x_studio_confezioni_richieste' not in fields:
            fields.append('x_studio_confezioni_richieste')
        return fields

