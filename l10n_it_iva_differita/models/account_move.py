import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResCompany(models.Model):
    """Aggiunge i campi di configurazione IVA differita alla società."""
    _inherit = 'res.company'

    account_iva_differita_id = fields.Many2one(
        comodel_name='account.account',
        string='Conto IVA differita',
        check_company=True,
    )
    journal_iva_differita_id = fields.Many2one(
        comodel_name='account.journal',
        string='Giornale IVA differita',
        check_company=True,
    )


class AccountMove(models.Model):
    _inherit = 'account.move'

    # ── Campo principale ──────────────────────────────────────────────────────
    iva_differita = fields.Boolean(
        string='IVA differita',
        default=False,
        copy=False,
        help="Se attivo, il conto Credito IVA viene sostituito con il conto "
             "IVA differita e al momento della conferma viene generata "
             "automaticamente una registrazione di storno.",
    )

    # Collegamento alla registrazione di storno creata automaticamente
    iva_differita_move_id = fields.Many2one(
        comodel_name='account.move',
        string='Registrazione IVA differita',
        readonly=True,
        copy=False,
        ondelete='set null',
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_iva_differita_config(self):
        """Restituisce (conto_iva_differita, giornale) per la società corrente."""
        company = self.company_id
        account = company.account_iva_differita_id
        journal = company.journal_iva_differita_id
        if not account:
            raise UserError(
                _("Configura il conto IVA differita nelle impostazioni contabili "
                  "(Contabilità → Configurazione → Impostazioni).")
            )
        if not journal:
            raise UserError(
                _("Configura il giornale IVA differita nelle impostazioni contabili "
                  "(Contabilità → Configurazione → Impostazioni).")
            )
        return account, journal

    @staticmethod
    def _last_day_of_month(ref_date):
        """Restituisce l'ultimo giorno del mese di ref_date."""
        next_month = ref_date.replace(day=1) + datetime.timedelta(days=32)
        return next_month.replace(day=1) - datetime.timedelta(days=1)

    # ── Override action_post ──────────────────────────────────────────────────

    def action_post(self):
        """Intercetta la conferma: se iva_differita, sostituisce i conti IVA
        e crea la registrazione automatica di storno."""
        for move in self:
            if move.iva_differita and move.move_type in ('in_invoice', 'in_refund'):
                move._apply_iva_differita_accounts()

        res = super().action_post()

        for move in self:
            if (
                move.iva_differita
                and move.move_type in ('in_invoice', 'in_refund')
                and move.state == 'posted'
                and not move.iva_differita_move_id
            ):
                storno = move._create_iva_differita_storno()
                move.iva_differita_move_id = storno.id

        return res

    # ── Sostituzione conti IVA sulle righe ───────────────────────────────────

    def _apply_iva_differita_accounts(self):
        """Sostituisce il conto Credito IVA con il conto IVA differita
        su tutte le righe di tipo 'tax' della fattura."""
        self.ensure_one()
        account_differita, _journal = self._get_iva_differita_config()

        # I conti IVA acquisti tipici: cerchiamo le righe con tax_line_id
        # (righe generate automaticamente dalla tassa) che abbiano un conto
        # di tipo credito IVA (account.account con tag IVA in Dare/Avere).
        # Sostituiamo il conto con quello IVA differita.
        iva_lines = self.line_ids.filtered(
            lambda l: l.tax_line_id and l.display_type == 'tax'
        )
        if not iva_lines:
            return

        for line in iva_lines:
            line.account_id = account_differita

    # ── Creazione registrazione di storno ─────────────────────────────────────

    def _create_iva_differita_storno(self):
        """Crea la registrazione di storno nel giornale Operazioni varie:
        - Data: ultimo giorno del mese precedente alla data contabile
        - Dare:  Credito IVA  (il conto originale della tassa)
        - Avere: IVA differita (il conto usato sulla fattura)
        """
        self.ensure_one()
        account_differita, journal = self._get_iva_differita_config()

        # Data della registrazione = ultimo giorno del mese della data fattura
        ref_date = self.invoice_date or self.date or fields.Date.context_today(self)
        storno_date = self._last_day_of_month(ref_date)

        # Raccogliamo le righe di tipo tax sulla fattura confermata
        iva_lines = self.line_ids.filtered(
            lambda l: l.tax_line_id and l.display_type == 'tax'
        )
        if not iva_lines:
            return self.env['account.move']

        # Recuperiamo il conto IVA "originale" dalla tassa stessa.
        # Se la tassa ha un conto di repartizione specifico lo usiamo,
        # altrimenti fallback al primo account_id trovato nella tassa.
        storno_line_vals = []
        for line in iva_lines:
            tax = line.tax_line_id
            # Conto Credito IVA: lo prendiamo dalle repartition line della tassa
            # (tipo 'tax', use_in_tax_closing=True o il primo disponibile).
            credito_iva_account = self._get_credito_iva_account(tax)
            if not credito_iva_account:
                raise UserError(
                    _("Impossibile determinare il conto Credito IVA per la tassa '%s'. "
                      "Verifica le righe di ripartizione della tassa.") % tax.name
                )

            amount = abs(line.balance)
            # Su fattura fornitore la riga IVA ha balance negativo (avere)
            # Storno: Dare = Credito IVA, Avere = IVA differita
            storno_line_vals.append({
                'account_id': credito_iva_account.id,
                'name': _('Storno IVA differita – %s') % (self.name or ''),
                'debit': amount,
                'credit': 0.0,
                'tax_line_id': False,
            })
            storno_line_vals.append({
                'account_id': account_differita.id,
                'name': _('Storno IVA differita – %s') % (self.name or ''),
                'debit': 0.0,
                'credit': amount,
                'tax_line_id': False,
            })

        move_vals = {
            'move_type': 'entry',
            'journal_id': journal.id,
            'date': storno_date,
            'ref': _('IVA differita – %s') % (self.name or ''),
            'line_ids': [(0, 0, v) for v in storno_line_vals],
            # Collegamento alla fattura originale
            'iva_differita_origin_id': self.id,
        }
        storno_move = self.env['account.move'].create(move_vals)
        # Confermiamo automaticamente la registrazione di storno
        storno_move.action_post()
        return storno_move

    def _get_credito_iva_account(self, tax):
        """Restituisce il conto Credito IVA associato alla tassa,
        cercando nelle repartition lines di tipo 'tax'."""
        # Repartition lines per acquisti (invoice)
        rep_lines = tax.invoice_repartition_line_ids.filtered(
            lambda r: r.repartition_type == 'tax' and r.account_id
        )
        if rep_lines:
            return rep_lines[0].account_id
        return False

    # ── Azione smart button ───────────────────────────────────────────────────

    def action_open_iva_differita_move(self):
        """Apre la registrazione di storno IVA differita collegata."""
        self.ensure_one()
        if not self.iva_differita_move_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Registrazione IVA differita'),
            'res_model': 'account.move',
            'res_id': self.iva_differita_move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Annullamento / reset ──────────────────────────────────────────────────

    def button_draft(self):
        """Se si rimette in bozza la fattura, annulla anche la registrazione
        di storno collegata (se ancora in bozza o confermata)."""
        for move in self:
            if move.iva_differita_move_id:
                storno = move.iva_differita_move_id
                if storno.state == 'posted':
                    storno.button_draft()
                storno.button_cancel()
                move.iva_differita_move_id = False
        return super().button_draft()

    # ── Onchange: avviso se mancano configurazioni ────────────────────────────

    @api.onchange('iva_differita')
    def _onchange_iva_differita(self):
        if self.iva_differita:
            company = self.company_id or self.env.company
            if not company.account_iva_differita_id:
                return {
                    'warning': {
                        'title': _('Configurazione mancante'),
                        'message': _(
                            "Il conto IVA differita non è configurato. "
                            "Vai in Contabilità → Configurazione → Impostazioni."
                        ),
                    }
                }


class AccountMoveIvaDifferita(models.Model):
    """Aggiunge il campo inverso sulla registrazione di storno."""
    _inherit = 'account.move'

    iva_differita_origin_id = fields.Many2one(
        comodel_name='account.move',
        string='Fattura origine IVA differita',
        readonly=True,
        copy=False,
        index=True,
    )
