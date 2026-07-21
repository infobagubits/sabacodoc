# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_it_rc_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Sezionale autofatture (default)",
        domain="[('type', '=', 'sale'), ('company_id', '=', id)]",
        help="Sezionale usato quando la posizione fiscale non ne indica uno.",
    )
    l10n_it_rc_receivable_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Conto contropartita autofattura (Credito, default)",
        domain="[('account_type', '=', 'asset_receivable'),"
               " ('company_ids', 'in', id)]",
    )
    l10n_it_rc_transitory_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Conto transitorio imponibile (default)",
        domain="[('account_type', 'not in',"
               " ('asset_receivable', 'liability_payable')),"
               " ('company_ids', 'in', id)]",
    )
