from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    show_discount3_purchase = fields.Boolean(
        compute='_compute_show_discount3_purchase',
        store=False
    )

    @api.depends('order_line')
    def _compute_show_discount3_purchase(self):
        config_param = self.env['ir.config_parameter'].sudo()
        qtd = config_param.get_param('purchase.enable_multiple_discounts_qtd', 'due')

        for order in self:
            order.show_discount3_purchase = (qtd == 'due')
    
    show_multiple_discounts_purchase = fields.Boolean(
        compute="_compute_show_multiple_discounts_purchase",
        store=False
    )

    @api.depends()
    def _compute_show_multiple_discounts_purchase(self):
        config = self.env['ir.config_parameter'].sudo().get_param('purchase.enable_multiple_discounts', 'False')
        is_enabled = config in ('True', '1', 'true')
        for order in self:
            order.show_multiple_discounts_purchase = is_enabled

