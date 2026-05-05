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

    # Campi per la calcolatrice
    calcolatrice_valore1 = fields.Float(
        string='Valore 1',
        default=0.0,
        help='Primo valore per il calcolo'
    )
    
    calcolatrice_operatore = fields.Selection(
        [
            ('*', '× (Moltiplicazione)'),
            ('/', '÷ (Divisione)'),
            ('-', '- (Sottrazione)'),
            ('+', '+ (Addizione)'),
        ],
        string='Operatore',
        default='*',
        help='Operatore matematico per il calcolo'
    )
    
    calcolatrice_valore2 = fields.Float(
        string='Valore 2',
        default=0.0,
        help='Secondo valore per il calcolo'
    )
    
    calcolatrice_risultato = fields.Float(
        string='Risultato',
        compute='_compute_calcolatrice_risultato',
        readonly=True,
        store=False,
        help='Risultato del calcolo automatico'
    )
    
    @api.depends('calcolatrice_valore1', 'calcolatrice_operatore', 'calcolatrice_valore2')
    def _compute_calcolatrice_risultato(self):
        """Calcola il risultato in base ai valori e all'operatore"""
        for line in self:
            valore1 = line.calcolatrice_valore1 or 0.0
            valore2 = line.calcolatrice_valore2 or 0.0
            operatore = line.calcolatrice_operatore or '*'
            
            try:
                if operatore == '*':
                    line.calcolatrice_risultato = valore1 * valore2
                elif operatore == '/':
                    line.calcolatrice_risultato = valore1 / valore2 if valore2 != 0 else 0.0
                elif operatore == '-':
                    line.calcolatrice_risultato = valore1 - valore2
                elif operatore == '+':
                    line.calcolatrice_risultato = valore1 + valore2
                else:
                    line.calcolatrice_risultato = 0.0
            except (ZeroDivisionError, TypeError):
                line.calcolatrice_risultato = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.mapped('picking_id')._sabaco_apply_l10n_it_parcels_from_move_lines()
        return lines

    def write(self, vals):
        pickings_before = self.mapped('picking_id')
        res = super().write(vals)
        (pickings_before | self.mapped('picking_id'))._sabaco_apply_l10n_it_parcels_from_move_lines()
        return res

    def unlink(self):
        pickings = self.mapped('picking_id')
        res = super().unlink()
        pickings._sabaco_apply_l10n_it_parcels_from_move_lines()
        return res

    def _get_fields_stock_barcode(self):
        """Estende os campos disponíveis no contexto JavaScript do barcode"""
        fields = super()._get_fields_stock_barcode()
        # Adiciona x_studio_confezioni_richieste se o campo existir no move_id
        # Verifica se existe no modelo stock.move antes de adicionar
        if hasattr(self.env['stock.move'], '_fields') and 'x_studio_confezioni_richieste' in self.env['stock.move']._fields:
            if 'x_studio_confezioni_richieste' not in fields:
                fields.append('x_studio_confezioni_richieste')
        return fields

