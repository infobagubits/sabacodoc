from odoo import _, models


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    # Il widget chiama _line_value_changed_<campo> per ogni campo modificato nel form.
    def _line_value_changed_deferred_start_date(self, line):
        self.ensure_one()
        self._lines_turn_auto_balance_into_manual_line(line)
        if line.deferred_start_date and (
            not line.deferred_end_date or line.deferred_end_date < line.deferred_start_date
        ):
            line.deferred_end_date = line.deferred_start_date

    def _line_value_changed_deferred_end_date(self, line):
        self.ensure_one()
        self._lines_turn_auto_balance_into_manual_line(line)

    def _action_validate(self):
        # Chiamato da "Valida", "Da controllare" e dal cron di riconciliazione automatica.
        # Il move della banca e' gia' confermato, quindi _post (che genera i differimenti
        # nelle fatture) non viene eseguito: i differimenti si annullano e rigenerano qui.
        move = self.st_line_id.move_id
        con_date = any(self.line_ids.mapped('deferred_start_date'))
        if not con_date and not move.deferred_move_ids:
            return super()._action_validate()

        # Le date sono visibili su ogni riga di contropartita, ma valgono solo per costi/ricavi.
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
