# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves.filtered(lambda m: m.state == 'posted')._sabaco_mark_partner_flags()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'posted':
            self._sabaco_mark_partner_flags()
        return res

    def _sabaco_mark_partner_flags(self):
        """Marca is_customer / is_supplier sui contatti delle fatture pubblicate."""
        for move in self:
            if move.state != 'posted':
                continue
            if move.move_type not in ('out_invoice', 'in_invoice'):
                continue

            partners = move.partner_id | move.commercial_partner_id
            if not partners:
                continue

            # sudo: l'utente che conferma la fattura potrebbe non avere
            # diritto di scrittura sul contatto; il flag è una regola di business.
            partners = partners.sudo()

            if move.move_type == 'out_invoice':
                to_mark = partners.filtered(lambda p: not p.is_customer)
                if to_mark:
                    to_mark.write({'is_customer': True})
                    _logger.info(
                        "sabaco_invoice_partner_flags: fattura %s (id=%s) "
                        "→ is_customer=True su partner %s",
                        move.name, move.id, to_mark.ids,
                    )
            elif move.move_type == 'in_invoice':
                to_mark = partners.filtered(lambda p: not p.is_supplier)
                if to_mark:
                    to_mark.write({'is_supplier': True})
                    _logger.info(
                        "sabaco_invoice_partner_flags: fattura %s (id=%s) "
                        "→ is_supplier=True su partner %s",
                        move.name, move.id, to_mark.ids,
                    )
