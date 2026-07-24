# -*- coding: utf-8 -*-
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _sabaco_get_invoice_lot_map(self):
        """Restituisce una mappa {product_id: "lotto_a, lotto_b"} per la stampa.

        Riusa il metodo core ``_get_invoiced_lot_values()`` (fornito da
        ``sale_stock``) invece di ricalcolare i lotti. Il metodo core aggrega a
        livello di fattura e ritorna una lista di dict con le chiavi
        ``product_name``, ``quantity``, ``uom_name``, ``lot_name`` e ``lot_id``.

        Attenzione: nel dict core ``lot_id`` e' l'**intero** id di ``stock.lot``,
        non un record; per ricavare il prodotto va fatto un ``browse``. La lettura
        avviene in ``sudo`` perche' l'utente che stampa puo' non avere accesso a
        ``stock.lot`` (stesso approccio del core).

        Ritorna ``{}`` per fatture senza lotti, fatture fornitore/non confermate
        o in caso di qualsiasi errore, cosi' da non rompere mai la stampa.
        """
        self.ensure_one()
        try:
            values = self._get_invoiced_lot_values()
            if not values:
                return {}

            # Ricava il prodotto di ogni lotto con un solo browse (in sudo).
            lot_ids = [v["lot_id"] for v in values if v.get("lot_id")]
            lots = self.env["stock.lot"].browse(lot_ids).sudo()
            lot_to_product = {lot.id: lot.product_id.id for lot in lots}

            # Aggrega i nomi lotto per prodotto, preservando l'ordine, senza duplicati.
            names_per_product = {}
            for val in values:
                lot_id = val.get("lot_id")
                lot_name = val.get("lot_name")
                if not lot_id or not lot_name:
                    continue
                product_id = lot_to_product.get(lot_id)
                if not product_id:
                    continue
                names = names_per_product.setdefault(product_id, [])
                if lot_name not in names:
                    names.append(lot_name)

            return {
                product_id: ", ".join(names)
                for product_id, names in names_per_product.items()
            }
        except Exception:
            # Difesa: la stampa non deve mai fallire per via dei lotti.
            return {}
