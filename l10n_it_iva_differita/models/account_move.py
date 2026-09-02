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
    def _last_day_of_previous_month(ref_date):
        """Restituisce l'ultimo giorno del mese precedente a quello di ref_date."""
        return ref_date.replace(day=1) - datetime.timedelta(days=1)

    # ── Override action_post ──────────────────────────────────────────────────

    def action_post(self):
        """Intercetta la conferma: se iva_differita, sostituisce i conti IVA
        e crea la registrazione automatica di storno."""
        differita_data_by_move = {}
        for move in self:
            if move.iva_differita and move.move_type in ('in_invoice', 'in_refund'):
                differita_data_by_move[move.id] = move._apply_iva_differita_accounts()

        res = super().action_post()

        for move in self:
            if (
                move.iva_differita
                and move.move_type in ('in_invoice', 'in_refund')
                and move.state == 'posted'
                and not move.iva_differita_move_id
            ):
                storno = move._create_iva_differita_storno(
                    differita_data_by_move.get(move.id, {})
                )
                move.iva_differita_move_id = storno.id

        return res

    # ── Sostituzione conti IVA sulle righe ───────────────────────────────────

    def _apply_iva_differita_accounts(self):
        """Sostituisce il conto Credito IVA con il conto IVA differita sulle
        righe imposta della fattura e rimuove i tag di griglia IVA sia dalla
        riga imposta sia dalle righe base (imponibile) collegate alla stessa
        tassa.

        Né l'importo IVA né l'imponibile devono comparire nel registro/nella
        liquidazione del mese della fattura: entrambi vengono riportati nel
        mese precedente tramite la registrazione di storno (vedi
        _create_iva_differita_storno). I dati originali (conto, importo, tag)
        vengono restituiti per essere usati nello storno.
        """
        self.ensure_one()
        account_differita, _journal = self._get_iva_differita_config()

        # Righe imposta generate dalla tassa
        iva_lines = self.line_ids.filtered(
            lambda l: l.tax_line_id and l.display_type == 'tax'
        )
        if not iva_lines:
            return {}

        # Righe base (imponibile) collegate alla/e stessa/e tassa/e
        taxes = iva_lines.tax_line_id
        base_lines = self.line_ids.filtered(
            lambda l: l.display_type == 'product' and (l.tax_ids & taxes)
        )

        differita_data = {}

        for line in base_lines:
            differita_data[line.id] = {
                'kind': 'base',
                'account_id': line.account_id.id,
                'amount': line.balance,
                'tags': line.tax_tag_ids.ids,
                'invert': line.tax_tag_invert,
                'tax_ids': line.tax_ids.ids,
            }
            line.tax_tag_ids = [(5, 0, 0)]
            line.tax_tag_invert = False

        for line in iva_lines:
            differita_data[line.id] = {
                'kind': 'tax',
                'account_id': line.account_id.id,
                'amount': line.balance,
                'tags': line.tax_tag_ids.ids,
                'invert': line.tax_tag_invert,
                'tax_id': line.tax_line_id.id,
            }
            line.account_id = account_differita
            line.tax_tag_ids = [(5, 0, 0)]
            line.tax_tag_invert = False

        return differita_data

    # ── Creazione registrazione di storno ─────────────────────────────────────

    def _create_iva_differita_storno(self, differita_data=None):
        """Crea la registrazione di storno nel giornale Operazioni varie,
        datata all'ultimo giorno del mese precedente alla fattura:

        - Riga imposta: Dare Credito IVA (conto originale) / Avere IVA
          differita, con tax_line_id impostato sulla tassa originale in modo
          che l'importo compaia nella tabella "Imposta applicata/Deducibile"
          del mese dello storno.
        - Riga base: coppia di righe sullo stesso conto imponibile originale
          (una a debito, una a credito, a saldo zero) dove solo la prima
          porta i tag di griglia IVA, così che l'imponibile risulti nella
          griglia del mese dello storno senza spostare l'effetto economico
          dal conto di costo/ricavo originale.
        """
        differita_data = differita_data or {}
        self.ensure_one()
        account_differita, journal = self._get_iva_differita_config()

        if not differita_data:
            return self.env['account.move']

        # Data della registrazione = ultimo giorno del mese precedente alla
        # data contabile della fattura (non alla data fattura/documento)
        ref_date = self.date or self.invoice_date or fields.Date.context_today(self)
        storno_date = self._last_day_of_previous_month(ref_date)

        # Distribuzione analitica: aggregata dalle righe prodotto della fattura
        analytic_distribution = self._get_aggregated_analytic_distribution()
        name = _('Storno IVA differita – %s') % (self.name or '')

        storno_line_vals = []
        for data in differita_data.values():
            amount = abs(data['amount'])
            analytic = analytic_distribution or False
            tag_ids = data['tags']
            tag_invert = data['invert']

            if data['kind'] == 'tax':
                # Storno: Dare = Credito IVA, Avere = IVA differita
                storno_line_vals.append({
                    'account_id': data['account_id'],
                    'name': name,
                    'debit': amount,
                    'credit': 0.0,
                    'tax_line_id': data['tax_id'],
                    'analytic_distribution': analytic,
                    'tax_tag_ids': [(6, 0, tag_ids)],
                    'tax_tag_invert': tag_invert,
                })
                storno_line_vals.append({
                    'account_id': account_differita.id,
                    'name': name,
                    'debit': 0.0,
                    'credit': amount,
                    'tax_line_id': False,
                    'analytic_distribution': analytic,
                })
            else:
                # Coppia a saldo zero sullo stesso conto imponibile: sposta
                # solo il tag di griglia IVA nel mese dello storno, senza
                # alterare il conto di costo/ricavo della fattura originale.
                positive = data['amount'] >= 0
                storno_line_vals.append({
                    'account_id': data['account_id'],
                    'name': name,
                    'debit': amount if positive else 0.0,
                    'credit': 0.0 if positive else amount,
                    'tax_ids': [(6, 0, data['tax_ids'])],
                    'analytic_distribution': analytic,
                    'tax_tag_ids': [(6, 0, tag_ids)],
                    'tax_tag_invert': tag_invert,
                })
                storno_line_vals.append({
                    'account_id': data['account_id'],
                    'name': name,
                    'debit': 0.0 if positive else amount,
                    'credit': amount if positive else 0.0,
                    'analytic_distribution': analytic,
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

    def _get_aggregated_analytic_distribution(self):
        """Restituisce una distribuzione analitica aggregata (media pesata)
        dalle righe prodotto della fattura, da usare sulle righe dello storno."""
        self.ensure_one()
        product_lines = self.line_ids.filtered(
            lambda l: l.display_type == 'product' and l.analytic_distribution
        )
        if not product_lines:
            return False
        # Se tutte le righe hanno la stessa distribuzione, la restituiamo direttamente
        distributions = [l.analytic_distribution for l in product_lines]
        if all(d == distributions[0] for d in distributions):
            return distributions[0]
        # Altrimenti usiamo la distribuzione della prima riga come fallback
        return distributions[0]

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
