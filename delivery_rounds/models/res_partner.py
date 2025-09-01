from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    giri_ordine_ids = fields.One2many(
        'giri.ordine.riga',
        'partner_id',
        string='Giri',
        help='Giri dove questo cliente è inserito',
        readonly=True
    )

    ordini_aperti_ids = fields.One2many(
        'sale.order',
        'partner_id',
        string='Ordini Aperti',
        help='Ordini aperti del cliente',
        readonly=True,
        domain=[('stato_preparazione', '!=', 'stampato')]
    )

    @api.depends('is_customer')
    def _compute_giri_ordine_ids(self):
        for partner in self:
            if partner.is_customer:
                partner.giri_ordine_ids = self.env['giri.ordine.riga'].search([
                    ('partner_id', '=', partner.id)
                ])
            else:
                partner.giri_ordine_ids = False

    @api.onchange('is_customer')
    def _onchange_is_customer(self):
        """Metodo per garantire che l'interfaccia si aggiorni quando il campo is_customer cambia"""
        return 