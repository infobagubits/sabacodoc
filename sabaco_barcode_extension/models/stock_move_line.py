# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # Campo computed com inverse para acessar x_studio_confezioni_richieste do move_id
    # Permite edição e sincronização com move_id
    x_studio_confezioni_richieste = fields.Float(
        string='Confezioni Richieste',
        compute='_compute_x_studio_confezioni_richieste',
        inverse='_inverse_x_studio_confezioni_richieste',
        store=False,
        help='Quantità confezioni richieste dal movimento associato'
    )

    @api.depends('move_id.x_studio_confezioni_richieste')
    def _compute_x_studio_confezioni_richieste(self):
        """Computa o valor de x_studio_confezioni_richieste a partir do move_id"""
        for line in self:
            if line.move_id and hasattr(line.move_id, 'x_studio_confezioni_richieste'):
                line.x_studio_confezioni_richieste = line.move_id.x_studio_confezioni_richieste
            else:
                line.x_studio_confezioni_richieste = False

    def _inverse_x_studio_confezioni_richieste(self):
        """Atualiza o valor em move_id quando o campo é editado"""
        for line in self:
            if line.move_id and hasattr(line.move_id, 'x_studio_confezioni_richieste'):
                line.move_id.x_studio_confezioni_richieste = line.x_studio_confezioni_richieste

    def _get_fields_stock_barcode(self):
        """Estende os campos disponíveis no contexto JavaScript do barcode"""
        fields = super()._get_fields_stock_barcode()
        # Adiciona x_studio_confezioni_richieste se o campo existir no move_id
        # Verifica se existe no modelo stock.move antes de adicionar
        if hasattr(self.env['stock.move'], '_fields') and 'x_studio_confezioni_richieste' in self.env['stock.move']._fields:
            if 'x_studio_confezioni_richieste' not in fields:
                fields.append('x_studio_confezioni_richieste')
        return fields

