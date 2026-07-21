# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    l10n_it_rc_enabled = fields.Boolean(
        string="Reverse charge (autofattura separata)",
        help="Se attivo, le fatture fornitore con questa posizione fiscale, al "
             "momento della registrazione (post), generano automaticamente "
             "un'autofattura nel sezionale dedicato.",
    )
    l10n_it_rc_default = fields.Boolean(
        string="Applica reverse charge di default",
        help="Se attivo, sulle fatture fornitore con questa posizione fiscale "
             "il flag 'Reverse charge' è preselezionato. Se disattivo, la "
             "posizione fiscale è comunque abilitata ma l'operatore attiva il "
             "flag manualmente quando serve.",
    )
    l10n_it_rc_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Sezionale autofatture",
        domain="[('type', '=', 'sale'), ('company_id', '=', company_id)]",
        help="Registro vendite dedicato alle autofatture da reverse charge. "
             "La numerazione dedicata è quella del sezionale.",
    )
    l10n_it_rc_receivable_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Conto contropartita autofattura (Credito)",
        domain="[('account_type', '=', 'asset_receivable'),"
               " ('company_ids', 'in', company_id)]",
        help="Conto di tipo Credito usato sulla riga dei termini di pagamento "
             "dell'autofattura (contropartita cliente 'fittizia'). Richiesto "
             "dal vincolo Odoo: su una vendita la riga di chiusura deve essere "
             "su un conto Credito.",
    )
    l10n_it_rc_transitory_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Conto transitorio imponibile (non Credito/Debito)",
        domain="[('account_type', 'not in',"
               " ('asset_receivable', 'liability_payable')),"
               " ('company_ids', 'in', company_id)]",
        help="Conto (NON di tipo Credito/Debito) usato sulla riga imponibile "
             "dell'autofattura, al posto di un conto di ricavo reale.",
    )
