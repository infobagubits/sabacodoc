# -*- coding: utf-8 -*-
from datetime import date

from odoo import fields, models
from odoo.tools.misc import format_date


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

    def _sabaco_get_invoice_ddt_values(self):
        """Restituisce ``[{'number': str, 'date': str}]`` dei DDT della fattura.

        Riusa il campo core ``l10n_it_ddt_ids`` (fornito da ``l10n_it_stock_ddt``),
        lo stesso che alimenta lo smart button "DDT" e i ``DatiDDT`` dell'XML EDI:
        e' un compute non memorizzato che risale dalle righe fattura agli ordini di
        vendita e da questi ai picking con ``l10n_it_ddt_number`` valorizzato.
        Nessuna logica duplicata.

        La data del DDT e' quella del picking: ``date_done`` (validazione della
        consegna, la stessa usata dall'EDI) con ripiego su ``scheduled_date`` se il
        picking non e' ancora ``done``. La formattazione avviene qui in Python
        perche' il template riceve dei ``dict`` e non un recordset, quindi
        ``t-field`` non e' disponibile.

        La lettura avviene in ``sudo`` perche' l'utente che stampa puo' non avere
        accesso a ``stock.picking``/``sale.order`` (stessa motivazione di
        ``_sabaco_get_invoice_lot_map``).

        Ritorna ``[]`` per le fatture fornitore, per quelle senza DDT o in caso di
        qualsiasi errore, cosi' da non rompere mai la stampa.
        """
        self.ensure_one()
        try:
            if self.move_type not in ("out_invoice", "out_refund"):
                return []

            seen = set()
            rows = []
            for picking in self.sudo().l10n_it_ddt_ids:
                number = picking.l10n_it_ddt_number
                if not number or number in seen:
                    continue
                seen.add(number)
                moment = picking.date_done or picking.scheduled_date
                raw = fields.Date.to_date(moment) if moment else False
                rows.append((
                    # I DDT senza data finiscono in testa, l'ordine resta stabile.
                    raw or date.min,
                    number,
                    {
                        "number": number,
                        "date": format_date(self.env, raw) if raw else "",
                    },
                ))

            rows.sort(key=lambda row: (row[0], row[1]))
            return [row[2] for row in rows]
        except Exception:
            # Difesa: la stampa non deve mai fallire per via dei DDT.
            return []
