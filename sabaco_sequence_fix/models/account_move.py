# -*- coding: utf-8 -*-
import re
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _deduce_sequence_number_reset(self, name):
        """Forza il reset a 'never' per numerazioni a solo progressivo.

        Odoo deduce dal nome della sequenza se il contatore si azzera per
        anno, per mese o mai ('never'), e da questo ricava se applicare il
        controllo cronologico data<->numero. Con un formato come ``10/N``
        il progressivo a 2 cifre può essere scambiato per un anno a 2 cifre,
        generando il falso errore "La data non è allineata con la sequenza".

        Regola dirimente: se il nome della sequenza contiene UN SOLO blocco
        di cifre, quel blocco è necessariamente il contatore. Non può esistere
        una componente anno (o mese) separata dal progressivo, quindi il reset
        è per forza 'never'. In tutti gli altri casi (es. ``2026/0001``, che
        contiene due blocchi di cifre) deleghiamo al comportamento standard.

        Questo elimina il falso positivo senza toccare le sequenze con anno
        esplicito e senza disattivare il controllo cronologico dove ha senso.
        """
        digit_runs = re.findall(r"\d+", name or "")
        if len(digit_runs) == 1:
            return "never"
        return super()._deduce_sequence_number_reset(name)
