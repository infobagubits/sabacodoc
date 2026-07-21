# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_it_rc_journal_id = fields.Many2one(
        related="company_id.l10n_it_rc_journal_id",
        readonly=False,
        string="Sezionale autofatture (default)",
    )
    l10n_it_rc_transitory_account_id = fields.Many2one(
        related="company_id.l10n_it_rc_transitory_account_id",
        readonly=False,
        string="Conto transitorio reverse charge (default)",
    )
