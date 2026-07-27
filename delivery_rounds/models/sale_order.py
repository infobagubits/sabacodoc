from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    _order = 'sequenza_consegna, id'

    giro_id = fields.Many2one(
        'giri.ordine',
        string="Giro di Consegna",
        groups='delivery_rounds.group_delivery_rounds_user',
    )
    sequenza_consegna = fields.Integer(
        string="Sequenza di Consegna",
        groups='delivery_rounds.group_delivery_rounds_user',
    )
    
    x_preparazione = fields.Selection([
        ('da_preparare', 'Da preparare'),
        ('in_preparazione', 'In preparazione'),
        ('consegnato', 'Consegnato')
    ], string='Stato preparazione', default='da_preparare')
    
    @api.model
    def default_get(self, fields_list):
        defaults = super(SaleOrder, self).default_get(fields_list)

        # Prende il giro_id e partner_id dal contesto
        giro_id = self.env.context.get('default_giro_id')
        partner_id = self.env.context.get('default_partner_id')

        if giro_id and partner_id:
            # Cerca la sequenza del cliente nel giro
            riga = self.env['giri.ordine.riga'].search([
                ('giro_id', '=', giro_id),
                ('partner_id', '=', partner_id)
            ], limit=1)
            
            if riga:
                defaults['sequenza_consegna'] = riga.sequence

        return defaults
    
    def action_open_sale_order_form(self):
        """Apre il sale order a schermo intero"""
        self.ensure_one()
        return {
            'name': f'Ordine {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',  # Forza schermo intero
        }

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.giro_id and order.partner_id:
                riga = self.env['giri.ordine.riga'].search([
                    ('giro_id', '=', order.giro_id.id),
                    ('partner_id', '=', order.partner_id.id),
                ], limit=1)
                if riga:
                    riga.write({'stato': 'ordinato'})
        return res