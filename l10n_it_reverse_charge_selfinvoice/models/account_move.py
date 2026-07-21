# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

L10N_IT_RC_INTEGRATION_TD = ("TD16", "TD17", "TD18", "TD19")


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
        posted = super()._post(soft=soft)
        for move in posted:
            if (
                move.move_type in ("in_invoice", "in_refund")
                and move.l10n_it_rc_is_reverse_charge
                and not move.l10n_it_rc_is_self_invoice
                and not move.l10n_it_rc_self_invoice_id
            ):
                move._l10n_it_rc_generate_self_invoice()
        return posted

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
        return {
            "move_type": move_type,
            "journal_id": journal.id,
            "company_id": self.company_id.id,
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "invoice_date": self.invoice_date or fields.Date.context_today(self),
            "date": self.date,
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
