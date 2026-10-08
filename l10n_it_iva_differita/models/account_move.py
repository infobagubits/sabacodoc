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
    account_iva_differita_imponibile_id = fields.Many2one(
        comodel_name='account.account',
        string='Conto transitorio imponibile IVA differita',
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
        help="La fattura va registrata usando direttamente la tassa IVA "
             "differita (con il proprio conto e collegata, tramite il "
             "campo 'Imposta originale' sulla tassa, a quella che "
             "sostituisce). Se questo campo è attivo, alla conferma "
             "vengono rimossi i tag di griglia IVA dalle righe e viene "
             "generata automaticamente una registrazione di storno che "
             "gira l'importo al Credito IVA originale.",
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
        """Restituisce (conto_iva_differita, giornale, conto_imponibile) per
        la società corrente."""
        company = self.company_id
        account = company.account_iva_differita_id
        journal = company.journal_iva_differita_id
        account_imponibile = company.account_iva_differita_imponibile_id
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
        if not account_imponibile:
            raise UserError(
                _("Configura il conto transitorio imponibile IVA differita nelle "
                  "impostazioni contabili (Contabilità → Configurazione → "
                  "Impostazioni).")
            )
        return account, journal, account_imponibile

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

    # ── Snapshot fattura originale ────────────────────────────────────────────

    def _apply_iva_differita_accounts(self):
        """La fattura viene registrata direttamente dall'utente con la tassa
        IVA differita (conto e tassa già corretti in riga): qui non si
        sostituisce più nulla, ci si limita a:

        - verificare che ogni tassa differita usata in fattura abbia
          un'imposta originale collegata (campo "Imposta originale" sulla
          tassa), necessaria per costruire lo storno;
        - rimuovere i tag di griglia IVA sia dalla riga imposta sia dalle
          righe base (imponibile), così che la fattura non compaia nella
          liquidazione IVA del mese corrente: l'imponibile e l'imposta
          vengono riportati nel mese precedente tramite la registrazione di
          storno (vedi _create_iva_differita_storno), che userà la tassa
          originale collegata;
        - fare uno snapshot dei dati necessari per costruire lo storno.
        """
        self.ensure_one()

        # Righe imposta generate dalla tassa differita
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

        missing = taxes.filtered(lambda t: not t.iva_differita_tax_id)
        if missing:
            raise UserError(_(
                "Le seguenti tasse non hanno un'imposta originale collegata "
                "(campo 'Imposta originale' sulla tassa, da configurare "
                "sulla tassa IVA differita): %s"
            ) % ', '.join(missing.mapped('display_name')))

        # ── Snapshot dei dati necessari per la registrazione di storno.
        differita_data = {}
        for line in base_lines:
            differita_data[line.id] = {
                'kind': 'base',
                'amount': line.balance,
                'tax_ids': line.tax_ids.ids,
            }
        for line in iva_lines:
            differita_tax = line.tax_line_id
            original_tax = differita_tax.iva_differita_tax_id
            original_rep_line = original_tax._get_matching_tax_repartition_line(
                self.move_type, line.tax_repartition_line_id,
            )
            plus_tax = differita_tax._get_iva_differita_plus_taxes()
            plus_rep_line = plus_tax._get_matching_tax_repartition_line(
                self.move_type, line.tax_repartition_line_id,
            )
            differita_data[line.id] = {
                'kind': 'tax',
                'amount': line.balance,
                'tax_base_amount': line.tax_base_amount,
                'differita_tax_id': differita_tax.id,
                'differita_account_id': line.account_id.id,
                'differita_repartition_line_id': line.tax_repartition_line_id.id,
                'plus_tax_id': plus_tax.id,
                'plus_repartition_line_id': plus_rep_line.id,
                'original_tax_id': original_tax.id,
                'original_account_id': original_rep_line.account_id.id,
                'original_repartition_line_id': original_rep_line.id,
                'original_tag_ids': original_rep_line.tag_ids.ids,
            }

        # ── Svuotamento griglie: la fattura con tassa differita non deve
        # comparire nella liquidazione IVA del mese corrente.
        ctx_lines = self.line_ids.with_context(skip_account_move_synchronization=True)
        for line in base_lines | iva_lines:
            ctx_lines.browse(line.id).write({
                'tax_tag_ids': [(5, 0, 0)],
                'tax_tag_invert': False,
            })

        return differita_data

    # ── Creazione registrazione di storno ─────────────────────────────────────

    def _create_iva_differita_storno(self, differita_data=None):
        """Crea la registrazione di storno nel giornale Operazioni varie,
        datata all'ultimo giorno del mese precedente alla fattura:

        - Riga imposta: Dare Credito IVA (conto e tassa originali) / Avere
          IVA differita (conto e tassa differita), con tax_line_id impostato
          sulla tassa originale in modo che l'importo compaia nella tabella
          "Imposta applicata/Deducibile" del mese dello storno.
        - Riga base: coppia di righe sullo stesso conto transitorio
          imponibile (una a debito, una a credito, a saldo zero), Dare con
          l'imposta originale (porta i tag di griglia IVA), Avere con
          l'imposta differita, così che l'imponibile risulti nella griglia
          del mese dello storno senza spostare l'effetto economico dal conto
          di costo/ricavo originale.
        """
        differita_data = differita_data or {}
        self.ensure_one()
        _account_differita, journal, account_imponibile = self._get_iva_differita_config()

        if not differita_data:
            return self.env['account.move']

        # Data della registrazione = ultimo giorno del mese precedente alla
        # data contabile della fattura (non alla data fattura/documento)
        ref_date = self.date or self.invoice_date or fields.Date.context_today(self)
        storno_date = self._last_day_of_previous_month(ref_date)

        name = _('Storno IVA differita – %s') % (self.name or '')
        imponibile_name = _('Imponibile per IVA differita - %s') % (self.name or '')

        storno_line_vals = []

        # ── Righe imposta: lette direttamente dalla fattura (già con conto e
        # tassa differita corretti), lo storno aggiunge la contropartita
        # Dare con conto e tassa originali.
        for data in differita_data.values():
            if data['kind'] != 'tax':
                continue
            amount = abs(data['amount'])
            # Storno: Dare = Credito IVA (originale), Avere = IVA differita
            storno_line_vals.append({
                'account_id': data['original_account_id'],
                'name': name,
                'debit': amount,
                'credit': 0.0,
                'tax_line_id': data['original_tax_id'],
                'tax_base_amount': data['tax_base_amount'],
                'tax_repartition_line_id': data['original_repartition_line_id'],
                'tax_tag_ids': [(6, 0, data['original_tag_ids'])],
            })
            storno_line_vals.append({
                'account_id': data['differita_account_id'],
                'name': name,
                'debit': 0.0,
                'credit': amount,
                # Tassa differita (+) (o quella della fattura se non
                # configurata): il registro IVA deve vedere imponibile e
                # imposta sulla stessa tassa.
                'tax_line_id': data['plus_tax_id'],
                'tax_repartition_line_id': data['plus_repartition_line_id'],
            })

        # Le righe base vengono raggruppate per tassa (differita, così come
        # presente in fattura): anche se la fattura ha più righe di
        # imponibile con la stessa imposta, viene creata una sola coppia di
        # righe (dare/avere) sul conto transitorio.
        base_groups = {}
        for data in differita_data.values():
            if data['kind'] != 'base':
                continue
            key = tuple(sorted(data['tax_ids']))
            group = base_groups.setdefault(key, {'amount': 0.0, 'tax_ids': data['tax_ids']})
            group['amount'] += data['amount']

        # Coppia a saldo zero sul conto transitorio imponibile IVA differita:
        # sposta il tag di griglia IVA nel mese dello storno, senza toccare
        # il conto di costo/ricavo della fattura originale.
        # Posizioni (indice nella lista) delle righe, per poter scrivere
        # `tax_ids` dopo la creazione senza che `_sync_dynamic_lines`
        # rigeneri/duplichi la riga imposta già creata esplicitamente qui
        # sopra.
        debit_line_positions = []
        credit_line_positions = []
        for group in base_groups.values():
            if not group['amount']:
                continue
            amount = abs(group['amount'])
            positive = group['amount'] >= 0

            differita_taxes = self.env['account.tax'].browse(group['tax_ids'])
            original_taxes = differita_taxes.mapped('iva_differita_tax_id')
            plus_taxes = differita_taxes._get_iva_differita_plus_taxes()
            original_tags = []
            for tax in original_taxes:
                original_tags += tax._get_tax_repartition_lines(
                    self.move_type, 'base'
                ).tag_ids.ids

            debit_vals = {
                'account_id': account_imponibile.id,
                'name': imponibile_name,
                'debit': amount,
                'credit': 0.0,
            }
            credit_vals = {
                'account_id': account_imponibile.id,
                'name': imponibile_name,
                'debit': 0.0,
                'credit': amount,
            }
            tag_vals = {'tax_tag_ids': [(6, 0, original_tags)]}
            if positive:
                debit_vals.update(tag_vals)
            else:
                credit_vals.update(tag_vals)
            # Dare = imposta originale, Avere = imposta differita (+) se
            # configurata, altrimenti quella differita già in fattura.
            debit_line_positions.append((len(storno_line_vals), original_taxes.ids))
            storno_line_vals.append(debit_vals)
            credit_line_positions.append((len(storno_line_vals), plus_taxes.ids))
            storno_line_vals.append(credit_vals)

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

        # `tax_ids` sulle righe dell'imponibile viene scritto solo ora (come
        # riferimento informativo) e con skip_invoice_sync=True, per non far
        # rigenerare a `_sync_dynamic_lines` la riga imposta già creata
        # esplicitamente qui sopra (che genererebbe un duplicato). Fatto
        # prima della conferma, così il resto della registrazione segue il
        # normale flusso di creazione (necessario perché il registro IVA
        # riconosca correttamente l'imposta come applicata/deducibile).
        for position, tax_ids in debit_line_positions + credit_line_positions:
            storno_move.line_ids[position].with_context(
                skip_invoice_sync=True
            ).write({'tax_ids': [(6, 0, tax_ids)]})

        # Confermiamo automaticamente la registrazione di storno
        storno_move.action_post()
        return storno_move

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

    def action_open_iva_differita_origin(self):
        """Apre la fattura fornitore di origine collegata a questa
        registrazione di storno IVA differita."""
        self.ensure_one()
        if not self.iva_differita_origin_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fattura origine'),
            'res_model': 'account.move',
            'res_id': self.iva_differita_origin_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
