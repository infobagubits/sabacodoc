from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    purchase_product_filter = fields.Boolean(
        string='Filtra prodotti negli acquisti',
        help='Attiva il filtro dei prodotti per fornitore negli ordini di acquisto',
        config_parameter='purchase.use_product_filter',
        default=False
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        param = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
        res['purchase_product_filter'] = param == 'True'
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('purchase.use_product_filter', str(self.purchase_product_filter))

    @api.model
    def _init_purchase_product_filter(self):
        """Forza il valore iniziale come False"""
        self.env['ir.config_parameter'].sudo().set_param('purchase.use_product_filter', 'False') 