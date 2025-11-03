# -*- coding: utf-8 -*-

from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_fields_stock_barcode(self):
        """Estende os campos disponíveis no contexto JavaScript do barcode"""
        fields = super()._get_fields_stock_barcode()
        # Não adiciona x_studio_confezioni_richieste aqui pois o campo não existe em stock.move.line
        # Se necessário, deve ser criado um campo related ou acessado via move_id no template
        return fields

