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
        account_differita, _journal, _account_imponibile = self._get_iva_differita_config()

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

        # ── Snapshot dei dati originali (prima di qualsiasi modifica), da
        # usare per la registrazione di storno.
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
        for line in iva_lines:
            differita_data[line.id] = {
                'kind': 'tax',
                'account_id': line.account_id.id,
                'amount': line.balance,
                'tags': line.tax_tag_ids.ids,
                'invert': line.tax_tag_invert,
                'tax_id': line.tax_line_id.id,
                'tax_base_amount': line.tax_base_amount,
                'tax_repartition_line_id': line.tax_repartition_line_id.id,
            }

        # ── Sostituzione delle imposte: si scrive solo `tax_ids` sulle righe
        # base e si lascia che Odoo rigeneri correttamente le righe imposta
        # collegate (con il relativo tax_repartition_line_id), così da non
        # rompere la coerenza interna tra riga imposta e sua ripartizione.
        for line in base_lines:
            mapped_taxes = line.tax_ids._get_iva_differita_mapped_taxes()
            if mapped_taxes != line.tax_ids:
                line.tax_ids = [(6, 0, mapped_taxes.ids)]

        # Le righe imposta potrebbero essere state rigenerate (nuovi id) a
        # seguito della sostituzione di tax_ids sulle righe base: le
        # rileggiamo. Le righe base mantengono invece il loro id originale.
        iva_lines = self.line_ids.filtered(
            lambda l: l.tax_line_id and l.display_type == 'tax'
        )

        # ── Spostamento conto IVA e svuotamento griglie: nessuna ulteriore
        # rigenerazione delle righe deve scattare qui.
        ctx_lines = self.line_ids.with_context(skip_account_move_synchronization=True)
        for line in base_lines:
            ctx_lines.browse(line.id).write({
                'tax_tag_ids': [(5, 0, 0)],
                'tax_tag_invert': False,
            })
        for line in iva_lines:
            ctx_lines.browse(line.id).write({
                'account_id': account_differita.id,
                'tax_tag_ids': [(5, 0, 0)],
                'tax_tag_invert': False,
            })

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
        account_differita, journal, account_imponibile = self._get_iva_differita_config()

        if not differita_data:
            return self.env['account.move']

        # Data della registrazione = ultimo giorno del mese precedente alla
        # data contabile della fattura (non alla data fattura/documento)
        ref_date = self.date or self.invoice_date or fields.Date.context_today(self)
        storno_date = self._last_day_of_previous_month(ref_date)

        name = _('Storno IVA differita – %s') % (self.name or '')
        imponibile_name = _('Imponibile per IVA differita - %s') % (self.name or '')

        storno_line_vals = []

        # Le righe base vengono raggruppate per tassa: anche se la fattura ha
        # più righe di imponibile con la stessa imposta, viene creata una
        # sola coppia di righe (dare/avere) sul conto transitorio.
        base_groups = {}
        for data in differita_data.values():
            if data['kind'] != 'base':
                continue
            key = tuple(sorted(data['tax_ids']))
            group = base_groups.setdefault(key, {
                'amount': 0.0,
                'tags': data['tags'],
                'invert': data['invert'],
                'tax_ids': data['tax_ids'],
            })
            group['amount'] += data['amount']

        for data in differita_data.values():
            if data['kind'] != 'tax':
                continue
            amount = abs(data['amount'])
            tax_name = self.env['account.tax'].browse(data['tax_id']).name or name
            # Storno: Dare = Credito IVA, Avere = IVA differita
            storno_line_vals.append({
                'account_id': data['account_id'],
                'name': tax_name,
                'debit': amount,
                'credit': 0.0,
                'tax_line_id': data['tax_id'],
                'tax_base_amount': data['tax_base_amount'],
                'tax_repartition_line_id': data['tax_repartition_line_id'],
                'tax_tag_ids': [(6, 0, data['tags'])],
                'tax_tag_invert': data['invert'],
            })
            storno_line_vals.append({
                'account_id': account_differita.id,
                'name': tax_name,
                'debit': 0.0,
                'credit': amount,
                'tax_line_id': False,
            })

        # Coppia a saldo zero sul conto transitorio imponibile IVA differita:
        # sposta il tag di griglia IVA nel mese dello storno, senza toccare
        # il conto di costo/ricavo della fattura originale.
        # Posizioni (indice nella lista) delle righe in Dare dell'imponibile,
        # per poter scrivere `tax_ids` dopo la creazione senza che
        # `_sync_dynamic_lines` rigeneri/duplichi la riga imposta già creata
        # esplicitamente qui sopra.
        debit_line_positions = []
        for group in base_groups.values():
            if not group['amount']:
                continue
            amount = abs(group['amount'])
            positive = group['amount'] >= 0
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
            tag_vals = {
                'tax_tag_ids': [(6, 0, group['tags'])],
                'tax_tag_invert': group['invert'],
            }
            if positive:
                debit_vals.update(tag_vals)
            else:
                credit_vals.update(tag_vals)
            debit_line_positions.append((len(storno_line_vals), group['tax_ids']))
            storno_line_vals.append(debit_vals)
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

        # `tax_ids` sulla riga in Dare dell'imponibile viene scritto solo ora
        # (come riferimento informativo, per coerenza con la fattura
        # originale) e con skip_invoice_sync=True, per non far rigenerare a
        # `_sync_dynamic_lines` la riga imposta già creata esplicitamente qui
        # sopra (che genererebbe un duplicato). Fatto prima della conferma,
        # così il resto della registrazione segue il normale flusso di
        # creazione (necessario perché il registro IVA riconosca
        # correttamente l'imposta come applicata/deducibile).
        for position, tax_ids in debit_line_positions:
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
