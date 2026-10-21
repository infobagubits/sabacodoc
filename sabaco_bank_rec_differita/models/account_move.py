from itertools import chain

from odoo import Command, _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _sabaco_is_movimento_banca(self):
        """Registrazione di una transazione bancaria (non una fattura)."""
        self.ensure_one()
        return self.is_entry() and bool(self.statement_line_id)

    def _get_deferred_entries_method(self):
        # Nella v18 una registrazione 'entry' usa sempre il metodo dei ricavi:
        # per la banca il metodo dipende dal gruppo dei conti delle righe con date
        # (stessa regola del core v19).
        if not self._sabaco_is_movimento_banca():
            return super()._get_deferred_entries_method()
        gruppi = set(self.line_ids.filtered('deferred_start_date').account_id.mapped('internal_group'))
        company = self.company_id
        if (
            'expense' in gruppi and 'income' in gruppi
            and company.generate_deferred_expense_entries_method != company.generate_deferred_revenue_entries_method
        ):
            raise UserError(_(
                "La transazione bancaria ha righe differite sia di costo sia di ricavo, ma i metodi di "
                "generazione dei differimenti per costi e ricavi sono diversi. Dividere la transazione "
                "in due operazioni."
            ))
        if 'expense' in gruppi:
            return company.generate_deferred_expense_entries_method
        return company.generate_deferred_revenue_entries_method

    def _generate_deferred_entries(self):
        # Il core v18 rifiuta le registrazioni 'entry' e deduce il tipo dal documento:
        # per la banca si genera per tipo (costo/ricavo) in base al conto della riga.
        # Logica copiata da account_accountant v18 (_generate_deferred_entries) con il
        # ciclo per tipo del core v19. Da rimuovere con la migrazione alla v19.
        self.ensure_one()
        if not self._sabaco_is_movimento_banca():
            return super()._generate_deferred_entries()
        if self.state != 'posted':
            return
        for deferred_type in ('expense', 'revenue'):
            gruppo = 'expense' if deferred_type == 'expense' else 'income'
            lines = self.line_ids.filtered(lambda l: (
                l.account_id.internal_group == gruppo
                and l.deferred_start_date
                and l.deferred_end_date
            ))
            if lines:
                self._sabaco_genera_differimenti_per_tipo(lines, deferred_type)

    def _sabaco_genera_differimenti_per_tipo(self, lines, deferred_type):
        company = self.company_id
        deferred_account = company.deferred_expense_account_id if deferred_type == 'expense' else company.deferred_revenue_account_id
        deferred_journal = company.deferred_expense_journal_id if deferred_type == 'expense' else company.deferred_revenue_journal_id
        if not deferred_journal:
            raise UserError(_("Please set the deferred journal in the accounting settings."))
        if not deferred_account:
            raise UserError(_("Please set the deferred accounts in the accounting settings."))

        moves_vals_to_create = []
        lines_vals_to_create = []
        lines_periods = []
        for line in lines:
            # Restituisce [] anche quando inizio, fine e data della banca cadono nello stesso mese.
            periods = line._get_deferred_periods()
            if not periods:
                continue
            ref = _("Deferral of %s", line.move_id.name or '')
            moves_vals_to_create.append({
                'move_type': 'entry',
                'deferred_original_move_ids': [Command.set(line.move_id.ids)],
                'journal_id': deferred_journal.id,
                'company_id': company.id,
                'partner_id': line.partner_id.id,
                'auto_post': 'at_date',
                'ref': ref,
                'name': False,
                'date': line.move_id.date,
            })
            lines_vals_to_create.append([
                self.env['account.move.line']._get_deferred_lines_values(account.id, coeff * line.balance, ref, line.analytic_distribution, line)
                for (account, coeff) in [(line.account_id, -1), (deferred_account, 1)]
            ])
            lines_periods.append((line, periods))
        if not moves_vals_to_create:
            return

        moves_fully_deferred = self.create(moves_vals_to_create)
        for move_fully_deferred, lines_vals in zip(moves_fully_deferred, lines_vals_to_create):
            for line_vals in lines_vals:
                line_vals['move_id'] = move_fully_deferred.id
        self.env['account.move.line'].create(list(chain(*lines_vals_to_create)))

        deferral_moves_vals = []
        deferral_moves_line_vals = []
        for (line, periods), move_vals in zip(lines_periods, moves_vals_to_create):
            remaining_balance = line.balance
            for period_index, period in enumerate(periods):
                force_balance = remaining_balance if period_index == len(periods) - 1 else None
                deferred_amounts = self._get_deferred_amounts_by_line(line, [period], deferred_type)[0]
                balance = deferred_amounts[period] if force_balance is None else force_balance
                remaining_balance -= line.currency_id.round(balance)
                deferral_moves_vals.append({**move_vals, 'date': period[1]})
                deferral_moves_line_vals.append([
                    {
                        **self.env['account.move.line']._get_deferred_lines_values(account.id, coeff * balance, move_vals['ref'], line.analytic_distribution, line),
                        'partner_id': line.partner_id.id,
                        'product_id': line.product_id.id,
                    }
                    for (account, coeff) in [(deferred_amounts['account_id'], 1), (deferred_account, -1)]
                ])

        deferral_moves = self.create(deferral_moves_vals)
        for deferral_move, lines_vals in zip(deferral_moves, deferral_moves_line_vals):
            for line_vals in lines_vals:
                line_vals['move_id'] = deferral_move.id
        self.env['account.move.line'].create(list(chain(*deferral_moves_line_vals)))

        to_unlink = deferral_moves.filtered(lambda move: move.currency_id.is_zero(move.amount_total))
        for move_fully_deferred in moves_fully_deferred:
            # Due registrazioni nello stesso mese con lo stesso importo si annullano a vicenda.
            deferred_move_ids = move_fully_deferred.deferred_original_move_ids.deferred_move_ids
            cancelling_moves = deferred_move_ids.filtered(lambda move:
                move_fully_deferred.date.replace(day=1) == move.date.replace(day=1)
                and move.amount_total == move_fully_deferred.amount_total
            )
            if len(cancelling_moves) == 2:
                to_unlink |= cancelling_moves
        to_unlink.unlink()
        (moves_fully_deferred + deferral_moves - to_unlink)._post(soft=True)

    def _sabaco_differimenti_attivi(self):
        """Differimenti non annullati, non stornati e che non sono essi stessi storni."""
        self.ensure_one()
        return self.deferred_move_ids.filtered(
            lambda m: m.state != 'cancel' and not m.reversed_entry_id and not m.reversal_move_ids
        )

    def _sabaco_annulla_differimenti(self):
        """Annulla (elimina, annulla o storna) i differimenti attivi della transazione.

        Stessa logica di AccountMove.button_draft di account_accountant.
        Restituisce True se c'erano differimenti attivi.
        """
        self.ensure_one()
        attivi = self._sabaco_differimenti_attivi()
        if not attivi:
            return False
        if any(len(differimento.deferred_original_move_ids) > 1 for differimento in attivi):
            raise UserError(_(
                "Non è possibile modificare una transazione i cui differimenti sono raggruppati "
                "con altre registrazioni."
            ))
        storni = attivi._unlink_or_reverse()
        if storni:
            for storno in storni:
                storno.with_context(skip_readonly_check=True).write({
                    'date': storno._get_accounting_date(storno.date, storno._affect_tax_report()),
                })
            self.deferred_move_ids |= storni
        return True

    def _sabaco_genera_differimenti_banca(self):
        """Genera i differimenti della transazione se ci sono righe con date (metodo alla conferma)."""
        self.ensure_one()
        if (
            self.state == 'posted'
            and any(self.line_ids.mapped('deferred_start_date'))
            and self._get_deferred_entries_method() == 'on_validation'
        ):
            self._generate_deferred_entries()
            return True
        return False
