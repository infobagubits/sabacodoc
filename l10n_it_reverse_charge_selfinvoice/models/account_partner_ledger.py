# -*- coding: utf-8 -*-
from odoo import models


class AccountPartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"

    def _l10n_it_rc_hidden_account_ids(self, report, options):
        """Conti Credito dedicati alle autofatture reverse charge (azienda e
        posizioni fiscali): le loro righe, autofattura e chiusura, sono
        solo tecniche e non devono comparire nel Partitario."""
        company_ids = report.get_report_company_ids(options)
        companies = self.env["res.company"].browse(company_ids)
        fiscal_positions = self.env["account.fiscal.position"].sudo().search([
            ("company_id", "in", company_ids),
            ("l10n_it_rc_receivable_account_id", "!=", False),
        ])
        return (
            companies.mapped("l10n_it_rc_receivable_account_id")
            | fiscal_positions.mapped("l10n_it_rc_receivable_account_id")
        ).ids

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(
            report, options, previous_options=previous_options
        )
        account_ids = self._l10n_it_rc_hidden_account_ids(report, options)
        if account_ids:
            options["forced_domain"] = options.get("forced_domain", []) + [
                ("account_id", "not in", account_ids)
            ]
