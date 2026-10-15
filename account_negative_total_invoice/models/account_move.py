import logging

from odoo import models

_logger = logging.getLogger(__name__)

# Tipi di documento per cui il controllo standard viene aggirato.
# Le note di credito (out_refund / in_refund) e le ricevute restano escluse.
NEGATIVE_TOTAL_MOVE_TYPES = ("out_invoice", "in_invoice")


class AccountMove(models.Model):
    _inherit = "account.move"

    def _is_negative_total_allowed(self):
        """True se la fattura ha totale negativo e l'azienda consente di registrarla."""
        self.ensure_one()
        return (
            self.state == "draft"
            and self.move_type in NEGATIVE_TOTAL_MOVE_TYPES
            and self.company_id.allow_negative_total_invoice
            and self.currency_id.compare_amounts(self.amount_total, 0.0) < 0
        )

    def _post(self, soft=True):
        """Aggira il controllo "You cannot validate an invoice with a negative total amount".

        In Odoo 18 il controllo è scritto direttamente dentro account.move._post()
        e non espone un hook. Per non riscrivere l'intero metodo, durante la
        validazione presentiamo nella cache il valore assoluto di amount_total
        per le sole fatture autorizzate. Il valore in cache non viene marcato come
        "dirty", quindi non viene mai scritto nel database; alla fine (anche in caso
        di errore) il campo viene invalidato e riletto dal database con il valore reale.

        Tutti gli altri controlli standard di _post restano attivi.
        """
        negative_moves = self.filtered(lambda m: m._is_negative_total_allowed())
        if not negative_moves:
            return super()._post(soft=soft)

        # Garantisce che il valore reale sia calcolato e salvato prima di toccare la cache.
        negative_moves.flush_recordset(["amount_total"])
        amount_field = self._fields["amount_total"]
        real_totals = {move.id: move.amount_total for move in negative_moves}
        for move in negative_moves:
            self.env.cache.set(move, amount_field, -real_totals[move.id])

        try:
            posted = super()._post(soft=soft)
        finally:
            negative_moves.invalidate_recordset(["amount_total"])

        for move in negative_moves & posted:
            _logger.info(
                "Registrata %s %s con totale negativo %s",
                move.move_type, move.name, real_totals[move.id],
            )
            move.message_post(
                body=self.env._(
                    "Documento registrato con importo totale negativo (%(amount)s).",
                    amount=move.currency_id.format(real_totals[move.id]),
                ),
            )
        return posted
