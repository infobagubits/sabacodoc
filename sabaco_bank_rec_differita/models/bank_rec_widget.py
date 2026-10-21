from odoo import _, models
from odoo.exceptions import UserError


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    # Il widget chiama _line_value_changed_<campo> per ogni campo modificato nel form.
    # Con l'intervallo di date arrivano entrambe le date in un solo aggiornamento.
    def _line_value_changed_deferred_start_date(self, line):
        self.ensure_one()
        if self._sabaco_differita_su_riconciliata(line):
            return
        self._lines_turn_auto_balance_into_manual_line(line)
        if line.deferred_start_date and (
            not line.deferred_end_date or line.deferred_end_date < line.deferred_start_date
        ):
            line.deferred_end_date = line.deferred_start_date

    def _line_value_changed_deferred_end_date(self, line):
        self.ensure_one()
        if self._sabaco_differita_su_riconciliata(line):
            return
        self._lines_turn_auto_balance_into_manual_line(line)

    def _sabaco_differita_su_riconciliata(self, line):
        """Transazione gia' riconciliata: le date vanno sulla registrazione e i differimenti si rifanno subito.

        Nella v19 il popup "Modifica riga" lo fa senza reset; nella v18 la riconciliazione
        e' in sola lettura, quindi la riga di costo/ricavo viene aggiornata qui.
        Restituisce True se la modifica e' stata gestita.
        """
        if self.state != 'reconciled' or line.flag != 'aml' or not line.sabaco_differita_ammessa:
            return False
        st_line = self.st_line_id
        move = st_line.move_id
        if st_line.inalterable_hash or move.inalterable_hash:
            raise UserError(_(
                "La transazione bancaria è protetta (hash): non è possibile modificare la data differita."
            ))
        inizio = line.deferred_start_date
        fine = line.deferred_end_date if inizio else False
        if inizio and (not fine or fine < inizio):
            fine = inizio
        line.deferred_end_date = fine

        riga = line.source_aml_id
        if riga.deferred_start_date == inizio and riga.deferred_end_date == fine:
            return True
        riga.write({'deferred_start_date': inizio, 'deferred_end_date': fine})
        annullati = move._sabaco_annulla_differimenti()
        generati = move._sabaco_genera_differimenti_banca()
        if annullati or generati:
            move.message_post(body=_("Registrazioni differite rigenerate dalla riconciliazione bancaria."))
        return True

    def _action_validate(self):
        # Chiamato da "Valida", "Da controllare" e dal cron di riconciliazione automatica.
        # Il move della banca e' gia' confermato, quindi _post (che genera i differimenti
        # nelle fatture) non viene eseguito: i differimenti si annullano e rigenerano qui.
        move = self.st_line_id.move_id
        con_date = any(self.line_ids.mapped('deferred_start_date'))
        if not con_date and not move.deferred_move_ids:
            return super()._action_validate()

        # Date rimaste su una riga il cui conto non e' piu' di costo/ricavo: valgono solo per costi/ricavi.
        conti_ignorati = self.line_ids.filtered(
            lambda l: l.deferred_start_date and not l.sabaco_differita_ammessa
        ).account_id
        annullati = move._sabaco_annulla_differimenti()
        res = super()._action_validate()
        generati = move._sabaco_genera_differimenti_banca()
        if annullati or generati:
            move.message_post(body=_("Registrazioni differite rigenerate dalla riconciliazione bancaria."))
        if conti_ignorati:
            move.message_post(body=_(
                "Date differite ignorate: il conto %s non è di costo o ricavo.",
                ", ".join(conti_ignorati.mapped('display_name')),
            ))
        return res
