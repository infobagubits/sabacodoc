from odoo import _, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_undo_reconciliation(self):
        # Reset della riconciliazione: le righe con le date spariscono, quindi
        # vanno annullati anche i differimenti generati da esse.
        for st_line in self:
            move = st_line.move_id
            if move.deferred_move_ids and move._sabaco_annulla_differimenti():
                move.message_post(body=_("Registrazioni differite annullate dal reset della riconciliazione bancaria."))
        return super().action_undo_reconciliation()
