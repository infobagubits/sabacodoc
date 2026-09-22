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

    # Conto transitorio per l'imponibile sulla registrazione di storno
    account_iva_differita_imponibile_id = fields.Many2one(
        comodel_name='account.account',
        string='Conto transitorio imponibile IVA differita',
        related='company_id.account_iva_differita_imponibile_id',
        readonly=False,
        help="Conto transitorio utilizzato al posto del conto di costo/ricavo "
             "originale per l'imponibile nella registrazione di storno IVA "
             "differita.",
    )

    # Giornale "Operazioni varie" per la registrazione automatica
    journal_iva_differita_id = fields.Many2one(
        comodel_name='account.journal',
        string='Giornale IVA differita',
        related='company_id.journal_iva_differita_id',
        readonly=False,
        help="Giornale usato per le registrazioni automatiche di storno IVA differita.",
    )
