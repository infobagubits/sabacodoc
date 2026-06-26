from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Conto IVA differita (da configurare)
    account_iva_differita_id = fields.Many2one(
        comodel_name='account.account',
        string='Conto IVA differita',
        related='company_id.account_iva_differita_id',
        readonly=False,
        help="Conto patrimoniale utilizzato come IVA differita (es. 'IVA sospesa').",
    )

    # Giornale "Operazioni varie" per la registrazione automatica
    journal_iva_differita_id = fields.Many2one(
        comodel_name='account.journal',
        string='Giornale IVA differita',
        related='company_id.journal_iva_differita_id',
        readonly=False,
        help="Giornale usato per le registrazioni automatiche di storno IVA differita.",
    )
