# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.osv import expression

# Campo creato via Studio su res.partner: esiste solo nel database, non nel repository.
NOME_ALTERNATIVO = 'x_studio_nome_alternativo'

# Solo per questi operatori "positivi" l'OR con il nome alternativo è semanticamente corretto.
OPERATORI_SUPPORTATI = ('ilike', 'like', '=ilike', '=like', '=')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def _search_display_name(self, operator, value):
        """Estende la ricerca del partner al campo Studio "Nome alternativo".

        Il dominio standard (nome, riferimento, P.IVA, ...) resta invariato: viene
        soltanto messo in OR con il nome alternativo. Se il campo Studio non esiste
        nel database, il metodo si comporta esattamente come il core.
        """
        domain = super()._search_display_name(operator, value)
        if NOME_ALTERNATIVO not in self._fields or operator not in OPERATORI_SUPPORTATI or not value:
            return domain
        return expression.OR([domain, [(NOME_ALTERNATIVO, operator, value)]])
