from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    page_offset_enabled = fields.Boolean(
        string="Attiva Numerazione Personalizzata",
        help="Permette di definire un numero iniziale per le pagine dei report",
        config_parameter='l10n_it_custom.page_offset_enabled',
        default=False,
    )
    
    page_offset = fields.Integer(
        string="Pagina Iniziale",
        help="Numero della prima pagina (es: 12 per iniziare dalla pagina 12)",
        config_parameter='l10n_it_custom.page_offset',
        default=1,
    )

    @api.onchange('page_offset_enabled')
    def _onchange_page_offset_enabled(self):
        if not self.page_offset_enabled:
            self.page_offset = 1 