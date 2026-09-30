import json
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

# Chiave ir.config_parameter (valore iniziale in data/ir_config_parameter.xml)
ANTICIPO_MADE_ON_LABEL_PARAM = 'sabaco_customizations.anticipo_made_on_label'


class AccountOnlineAccount(models.Model):
    _inherit = 'account.online.account'

    def _format_transactions(self, new_transactions):
        """Per i movimenti di anticipo fatture usa ``made_on`` come data.

        Il proxy della sincronizzazione online restituisce come ``date`` la
        data di contabilizzazione della banca; per gli anticipi S.B.F. la data
        corretta è ``made_on`` (tab *Dettagli operazione*). La regola si applica
        solo se l'etichetta (``payment_ref``) contiene il testo configurato
        (case-insensitive); in ogni altro caso la data resta invariata.
        """
        res = super()._format_transactions(new_transactions)
        # sudo(): lettura di un parametro di sistema; la sincronizzazione
        # gira anche come utente contabile senza diritti su ir.config_parameter.
        label = (self.env['ir.config_parameter'].sudo().get_param(ANTICIPO_MADE_ON_LABEL_PARAM) or '').strip()
        if not label:
            return res
        label = label.casefold()
        for transaction in res:
            payment_ref = transaction.get('payment_ref')
            if not payment_ref or label not in payment_ref.casefold():
                continue
            made_on = self._sabaco_get_made_on(transaction.get('transaction_details'))
            if made_on and made_on != transaction['date']:
                _logger.info(
                    "Anticipo fatture: transazione %s, data %s sostituita con made_on %s",
                    transaction.get('online_transaction_identifier'), transaction['date'], made_on,
                )
                transaction['date'] = made_on
        return res

    def _sabaco_get_made_on(self, details):
        """Restituisce ``made_on`` di ``transaction_details`` come date, o False.

        ``transaction_details`` può arrivare come stringa JSON o come dict
        (stesso parse del core in ``bank_rec_widget``).
        """
        if not details:
            return False
        if isinstance(details, str):
            try:
                details = json.loads(details, strict=False)
            except ValueError:
                return False
        if not isinstance(details, dict):
            return False
        made_on = details.get('made_on')
        if not made_on or not isinstance(made_on, str):
            return False
        try:
            return fields.Date.from_string(made_on)
        except (ValueError, TypeError):
            return False
