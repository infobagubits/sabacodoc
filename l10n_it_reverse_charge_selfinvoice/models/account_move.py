# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

L10N_IT_RC_INTEGRATION_TD = ("TD16", "TD17", "TD18", "TD19")
L10N_IT_RC_TAX_ACCOUNT_CODE = "350101"
L10N_IT_RC_TAX_TRANSIT_ACCOUNT_CODE = "350123"


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_it_rc_is_reverse_charge = fields.Boolean(
        string="Reverse charge",
        compute="_compute_l10n_it_rc_is_reverse_charge",
        store=True,
        readonly=False,
        copy=False,
        help="Se attivo, alla registrazione della fattura fornitore viene "
             "generata l'autofattura separata. Precompilato dalla posizione "
             "fiscale, modificabile manualmente.",
    )
    l10n_it_rc_is_self_invoice = fields.Boolean(
        string="È un'autofattura",
        copy=False,
        readonly=True,
        help="Contrassegna i documenti generati automaticamente come "
             "autofattura da reverse charge.",
    )
    l10n_it_rc_self_invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Autofattura",
        copy=False,
        readonly=True,
        help="Autofattura generata da questa fattura fornitore.",
    )
    l10n_it_rc_origin_invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Fattura di origine",
        copy=False,
        readonly=True,
        help="Fattura fornitore che ha originato questa autofattura.",
    )

    # ------------------------------------------------------------------
    # Garantisce l'esistenza dei TipoDocumento di integrazione TD16-19
    # (record standard di l10n_it_edi_ndd). Idempotente: crea solo i mancanti.
    # Richiamato da data/l10n_it_document_type_ensure.xml a ogni update.
    # ------------------------------------------------------------------
    @api.model
    def _l10n_it_rc_ensure_document_types(self):
        Doc = self.env["l10n_it.document.type"]
        wanted = [
            ("TD16", "Reverse charged vendor bill integration for domestic "
                     "reverse charge"),
            ("TD17", "Reverse charged vendor bill integration for purchase of "
                     "foreign services"),
            ("TD18", "Reverse charged vendor bill integration for the purchase "
                     "of intra-EU goods"),
            ("TD19", "Reverse charged vendor bill integration for purchase of "
                     "goods from foreign markets"),
        ]
        existing = set(
            Doc.search([("code", "in", [c for c, _n in wanted])]).mapped("code")
        )
        to_create = [
            {"code": code, "name": name}
            for code, name in wanted
            if code not in existing
        ]
        if to_create:
            Doc.create(to_create)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends("fiscal_position_id", "move_type")
    def _compute_l10n_it_rc_is_reverse_charge(self):
        for move in self:
            if move.move_type in ("in_invoice", "in_refund"):
                fp = move.fiscal_position_id
                move.l10n_it_rc_is_reverse_charge = bool(
                    fp.l10n_it_rc_enabled and fp.l10n_it_rc_default
                )
            else:
                move.l10n_it_rc_is_reverse_charge = False

    # ------------------------------------------------------------------
    # EDI overrides (FatturaPA / SdI) for self-invoices
    # ------------------------------------------------------------------
    def _compute_l10n_it_edi_is_self_invoice(self):
        # Odoo calcola self-invoice solo per i documenti d'acquisto con tag VJ.
        # Le nostre autofatture di vendita di integrazione, quando hanno un
        # TipoDocumento (standard l10n_it_document_type) TD16/17/18/19, vanno
        # trattate come self-invoice così che l'XML inverta le parti
        # (CedentePrestatore = fornitore, CessionarioCommittente = azienda).
        super()._compute_l10n_it_edi_is_self_invoice()
        for move in self:
            code = move.l10n_it_document_type.code
            if move.l10n_it_rc_is_self_invoice and code in L10N_IT_RC_INTEGRATION_TD:
                move.l10n_it_edi_is_self_invoice = True

    # Il TipoDocumento nell'XML è gestito da 'l10n_it_edi_ndd' tramite il campo
    # standard l10n_it_document_type: nessun override necessario qui.

    # ------------------------------------------------------------------
    # Gestione autonoma delle griglie IVA (VJ) dell'autofattura
    # ------------------------------------------------------------------
    def _l10n_it_rc_td_vj_mapping(self):
        """ TipoDocumento -> codice griglia VJ (imponibile reverse charge).
            TD16 (interno) dipende dall'operazione (VJ6/7/8/12-17) e non viene
            assegnato automaticamente: in quel caso il tag resta quello
            dell'imposta configurata. """
        return {
            "TD17": "VJ3",   # servizi da non residenti
            "TD18": "VJ9",   # beni intracomunitari
            "TD19": "VJ3",   # beni gia' presenti in Italia da non residenti
        }

    def _l10n_it_rc_vj_report_lines(self, codes):
        if not codes:
            return self.env["account.report.line"]
        return self.env["account.report.line"].sudo().search([
            ("report_id.country_id.code", "=", "IT"),
            ("code", "in", list(codes)),
        ])

    def _l10n_it_rc_all_vj_tags(self):
        lines = self.env["account.report.line"].sudo().search([
            ("report_id.country_id.code", "=", "IT"),
            ("code", "=like", "VJ%"),
        ])
        return lines.expression_ids._get_matching_tags()

    def _l10n_it_rc_apply_edi_tax_grids(self):
        """ Assegna in autonomia il tag della griglia VJ corretta alle righe
            imponibile dell'autofattura, in base al TipoDocumento standard
            (l10n_it_document_type). Rimuove prima ogni VJ presente ed applica
            il tag col segno che rende l'imponibile positivo in dichiarazione. """
        all_vj = self._l10n_it_rc_all_vj_tags()
        for move in self.filtered(lambda m: m.l10n_it_rc_is_self_invoice):
            code = move._l10n_it_rc_td_vj_mapping().get(
                move.l10n_it_document_type.code
            )
            report_lines = move._l10n_it_rc_vj_report_lines([code] if code else [])
            plus_tags = report_lines.expression_ids._get_matching_tags("+")
            minus_tags = report_lines.expression_ids._get_matching_tags("-")
            for line in move.line_ids.filtered(lambda l: l.display_type == "product"):
                wanted = self.env["account.account.tag"]
                if code:
                    wanted = minus_tags if line.balance < 0 else plus_tags
                new_tags = (line.tax_tag_ids - all_vj) | wanted
                if set(new_tags.ids) != set(line.tax_tag_ids.ids):
                    line.tax_tag_ids = [(6, 0, new_tags.ids)]

    def write(self, vals):
        res = super().write(vals)
        if "l10n_it_document_type" in vals:
            self._l10n_it_rc_apply_edi_tax_grids()
        return res

    # ------------------------------------------------------------------
    # Posting hook
    # ------------------------------------------------------------------
    def _post(self, soft=True):
        for move in self:
            if (
                move.move_type in ("in_invoice", "in_refund")
                and move.l10n_it_rc_is_reverse_charge
                and not move.l10n_it_rc_is_self_invoice
            ):
                move._l10n_it_rc_split_payable_net_of_tax()
        posted = super()._post(soft=soft)
        for move in posted:
            if (
                move.move_type in ("in_invoice", "in_refund")
                and move.l10n_it_rc_is_reverse_charge
                and not move.l10n_it_rc_is_self_invoice
            ):
                move._l10n_it_rc_reconcile_tax_transit()
            if (
                move.move_type in ("in_invoice", "in_refund")
                and move.l10n_it_rc_is_reverse_charge
                and not move.l10n_it_rc_is_self_invoice
                and not move.l10n_it_rc_self_invoice_id
            ):
                move._l10n_it_rc_generate_self_invoice()
        return posted

    # ------------------------------------------------------------------
    # IVA al netto: la fattura fornitore in reverse charge non deve
    # generare un debito verso il fornitore comprensivo di IVA, perche'
    # l'imposta viene autoliquidata con l'autofattura e non versata al
    # fornitore.
    # ------------------------------------------------------------------
    def _l10n_it_rc_get_tax_transit_accounts(self):
        self.ensure_one()
        Account = self.env["account.account"]
        account_from = Account.search([
            ("code", "=", L10N_IT_RC_TAX_ACCOUNT_CODE),
            ("company_id", "=", self.company_id.id),
        ], limit=1)
        account_to = Account.search([
            ("code", "=", L10N_IT_RC_TAX_TRANSIT_ACCOUNT_CODE),
            ("company_id", "=", self.company_id.id),
        ], limit=1)
        if not account_from or not account_to:
            raise UserError(_(
                "Per gestire il reverse charge servono i conti %(a)s e "
                "%(b)s nel piano dei conti dell'azienda '%(c)s'."
            ) % {
                "a": L10N_IT_RC_TAX_ACCOUNT_CODE,
                "b": L10N_IT_RC_TAX_TRANSIT_ACCOUNT_CODE,
                "c": self.company_id.name,
            })
        if not account_to.reconcile:
            raise UserError(_(
                "Il conto %(code)s (%(name)s) deve avere l'opzione "
                "'Riconciliabile' attiva per gestire il reverse charge."
            ) % {"code": account_to.code, "name": account_to.name})
        return account_from, account_to

    def _l10n_it_rc_split_payable_net_of_tax(self):
        """Sposta le righe IVA della fattura fornitore dal conto %(a)s al
        conto transitorio %(b)s e scorpora il medesimo importo dalla riga
        di debito v/fornitore: l'importo che resta aperto/da pagare e'
        cosi' solo l'imponibile. La riga aggiunta sul conto transitorio
        viene poi riconciliata con la riga IVA (vedi
        _l10n_it_rc_reconcile_tax_transit), azzerando il conto."""
        self.ensure_one()
        account_from, account_to = self._l10n_it_rc_get_tax_transit_accounts()
        tax_lines = self.line_ids.filtered(
            lambda l: l.display_type == "tax" and l.account_id == account_from
        )
        if not tax_lines:
            return
        tax_lines.account_id = account_to.id

        term_lines = self.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        )
        if not term_lines:
            return
        tax_balance = sum(tax_lines.mapped("balance"))
        tax_amount_currency = sum(tax_lines.mapped("amount_currency"))
        if self.company_id.currency_id.is_zero(tax_balance):
            return

        first_term = term_lines[0]
        first_term.balance = first_term.balance + tax_balance
        first_term.amount_currency = first_term.amount_currency + tax_amount_currency

        self.line_ids = [(0, 0, {
            "name": first_term.name,
            "display_type": "payment_term",
            "account_id": account_to.id,
            "partner_id": first_term.partner_id.id,
            "currency_id": self.currency_id.id,
            "balance": -tax_balance,
            "amount_currency": -tax_amount_currency,
        })]

    def _l10n_it_rc_reconcile_tax_transit(self):
        self.ensure_one()
        _account_from, account_to = self._l10n_it_rc_get_tax_transit_accounts()
        lines = self.line_ids.filtered(
            lambda l: l.account_id == account_to and not l.reconciled
        )
        if len(lines) > 1:
            lines.reconcile()

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _l10n_it_rc_get_journal(self):
        self.ensure_one()
        return (
            self.fiscal_position_id.l10n_it_rc_journal_id
            or self.company_id.l10n_it_rc_journal_id
        )

    def _l10n_it_rc_get_transitory_account(self):
        self.ensure_one()
        return (
            self.fiscal_position_id.l10n_it_rc_transitory_account_id
            or self.company_id.l10n_it_rc_transitory_account_id
        )

    def _l10n_it_rc_get_receivable_account(self):
        self.ensure_one()
        return (
            self.fiscal_position_id.l10n_it_rc_receivable_account_id
            or self.company_id.l10n_it_rc_receivable_account_id
        )

    # ------------------------------------------------------------------
    # Self-invoice generation
    # ------------------------------------------------------------------
    def _l10n_it_rc_prepare_self_invoice_line(self, line, transitory_account):
        """Mappa una riga della fattura fornitore in una riga dell'autofattura."""
        self.ensure_one()
        mapped_taxes = line.tax_ids.mapped("l10n_it_rc_self_invoice_tax_id")
        if line.tax_ids and not mapped_taxes:
            raise UserError(_(
                "Impossibile generare l'autofattura: l'imposta '%(taxes)s' non "
                "ha un'imposta di autofattura mappata.\n"
                "Configurala in Contabilità > Configurazione > Imposte, campo "
                "'Imposta autofattura (reverse charge)'."
            ) % {"taxes": ", ".join(line.tax_ids.mapped("name"))})
        return {
            "display_type": "product",
            "product_id": line.product_id.id,
            "name": line.name,
            "quantity": line.quantity,
            "price_unit": line.price_unit,
            "discount": line.discount,
            "product_uom_id": line.product_uom_id.id,
            "account_id": transitory_account.id,
            "tax_ids": [(6, 0, mapped_taxes.ids)],
        }

    def _l10n_it_rc_prepare_self_invoice_values(self):
        self.ensure_one()
        journal = self._l10n_it_rc_get_journal()
        transitory_account = self._l10n_it_rc_get_transitory_account()
        receivable_account = self._l10n_it_rc_get_receivable_account()
        if not journal:
            raise UserError(_(
                "Nessun sezionale autofatture configurato. Impostalo sulla "
                "posizione fiscale '%s' oppure nei parametri contabili "
                "dell'azienda."
            ) % (self.fiscal_position_id.display_name or ""))
        if not transitory_account:
            raise UserError(_(
                "Nessun conto transitorio imponibile configurato. Impostalo "
                "sulla posizione fiscale '%s' oppure nei parametri contabili "
                "dell'azienda."
            ) % (self.fiscal_position_id.display_name or ""))
        if not receivable_account:
            raise UserError(_(
                "Nessun conto contropartita (Credito) configurato per "
                "l'autofattura. Impostalo sulla posizione fiscale '%s' oppure "
                "nei parametri contabili dell'azienda."
            ) % (self.fiscal_position_id.display_name or ""))
        if transitory_account.account_type in (
            "asset_receivable", "liability_payable"
        ):
            raise UserError(_(
                "Il conto transitorio imponibile (%s) non deve essere di tipo "
                "Credito/Debito, altrimenti la riga imponibile viola il vincolo "
                "contabile di Odoo."
            ) % transitory_account.display_name)
        if receivable_account.account_type != "asset_receivable":
            raise UserError(_(
                "Il conto contropartita autofattura (%s) deve essere di tipo "
                "Credito."
            ) % receivable_account.display_name)

        product_lines = self.invoice_line_ids.filtered(
            lambda l: l.display_type == "product"
        )
        line_vals = [
            (0, 0, self._l10n_it_rc_prepare_self_invoice_line(l, transitory_account))
            for l in product_lines
        ]
        move_type = "out_invoice" if self.move_type == "in_invoice" else "out_refund"
        immediate_term = self.env.ref(
            "account.account_payment_term_immediate", raise_if_not_found=False
        )
        return {
            "move_type": move_type,
            "journal_id": journal.id,
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "invoice_date": self.invoice_date or fields.Date.context_today(self),
            "date": self.date,
            # L'autofattura non deve mai risultare da incassare: termine di
            # pagamento immediato, poi la riga viene chiusa per
            # riconciliazione in _l10n_it_rc_close_self_invoice_receivable.
            "invoice_payment_term_id": immediate_term.id if immediate_term else False,
            "invoice_origin": self.name,
            "ref": _("Autofattura reverse charge - %s") % (
                self.name or self.ref or ""
            ),
            "l10n_it_rc_is_self_invoice": True,
            "l10n_it_rc_origin_invoice_id": self.id,
            "l10n_it_rc_is_reverse_charge": False,
            "invoice_line_ids": line_vals,
        }

    def _l10n_it_rc_generate_self_invoice(self):
        self.ensure_one()
        receivable_account = self._l10n_it_rc_get_receivable_account()
        transitory_account = self._l10n_it_rc_get_transitory_account()
        vals = self._l10n_it_rc_prepare_self_invoice_values()
        self_invoice = self.env["account.move"].create(vals)

        # La riga di contropartita (termini di pagamento) viene ricondotta al
        # conto Credito dedicato: l'autofattura non deve generare un credito
        # reale verso il fornitore. Il conto deve essere di tipo Credito per
        # rispettare il vincolo Odoo sulle righe con data di scadenza.
        term_lines = self_invoice.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        )
        if term_lines:
            term_lines.write({"account_id": receivable_account.id})

        self_invoice.action_post()
        # Alla registrazione, l10n_it_edi_ndd calcola un TipoDocumento di
        # vendita (es. TD01). Lo azzeriamo: dev'essere l'operatore a scegliere
        # il TD di integrazione corretto (TD16/17/18/19), che poi attiva
        # l'inversione delle parti e l'assegnazione delle griglie VJ.
        if "l10n_it_document_type" in self_invoice._fields:
            self_invoice.l10n_it_document_type = False
        self_invoice._l10n_it_rc_close_self_invoice_receivable(transitory_account)
        self.l10n_it_rc_self_invoice_id = self_invoice.id
        self.message_post(body=_(
            "Generata autofattura <b>%(name)s</b> nel sezionale %(journal)s."
        ) % {
            "name": self_invoice.name,
            "journal": self_invoice.journal_id.display_name,
        })
        self_invoice.message_post(body=_(
            "Autofattura generata automaticamente dalla fattura fornitore "
            "<b>%s</b> (reverse charge)."
        ) % (self.name or self.ref or ""))
        return self_invoice

    def _l10n_it_rc_close_self_invoice_receivable(self, transitory_account):
        """Chiude per riconciliazione la riga di credito v/cliente
        dell'autofattura: l'autofattura e' un documento fiscale, non deve
        generare un incasso reale ne' risultare da incassare. La
        contropartita di chiusura viene registrata sul conto transitorio
        imponibile gia' usato dalle righe prodotto dell'autofattura."""
        self.ensure_one()
        term_lines = self.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        )
        if not term_lines:
            return
        total_balance = sum(term_lines.mapped("balance"))
        total_amount_currency = sum(term_lines.mapped("amount_currency"))
        if self.company_id.currency_id.is_zero(total_balance):
            return

        receivable_account = term_lines[0].account_id
        closing_move = self.env["account.move"].create({
            "move_type": "entry",
            "journal_id": self.journal_id.id,
            "date": self.date,
            "ref": _("Chiusura autofattura reverse charge - %s") % (
                self.name or ""
            ),
            "line_ids": [
                (0, 0, {
                    "name": _("Chiusura autofattura %s") % (self.name or ""),
                    "account_id": receivable_account.id,
                    "partner_id": self.partner_id.id,
                    "currency_id": self.currency_id.id,
                    "balance": -total_balance,
                    "amount_currency": -total_amount_currency,
                }),
                (0, 0, {
                    "name": _("Chiusura autofattura %s") % (self.name or ""),
                    "account_id": transitory_account.id,
                    "partner_id": self.partner_id.id,
                    "currency_id": self.currency_id.id,
                    "balance": total_balance,
                    "amount_currency": total_amount_currency,
                }),
            ],
        })
        closing_move.action_post()
        (term_lines + closing_move.line_ids.filtered(
            lambda l: l.account_id == receivable_account
        )).reconcile()

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------
    def button_draft(self):
        for move in self:
            if move.l10n_it_rc_self_invoice_id and \
                    move.l10n_it_rc_self_invoice_id.state == "posted":
                raise UserError(_(
                    "Questa fattura ha un'autofattura collegata (%s) ancora "
                    "registrata. Storna o annulla prima l'autofattura, poi "
                    "riporta in bozza questa fattura."
                ) % move.l10n_it_rc_self_invoice_id.name)
        return super().button_draft()

    def unlink(self):
        linked = self.filtered(lambda m: m.l10n_it_rc_self_invoice_id)
        if linked:
            raise UserError(_(
                "Impossibile eliminare una fattura con autofattura collegata. "
                "Gestisci prima l'autofattura: %s"
            ) % ", ".join(linked.mapped("l10n_it_rc_self_invoice_id.name")))
        return super().unlink()

    # ------------------------------------------------------------------
    # Smart buttons
    # ------------------------------------------------------------------
    def l10n_it_rc_action_open_self_invoice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.l10n_it_rc_self_invoice_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def l10n_it_rc_action_open_origin(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": self.l10n_it_rc_origin_invoice_id.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }
