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
    
    @api.model
    def default_get(self, fields_list):
        """Força o contexto a carregar os valores na criação do pedido"""
        res = super().default_get(fields_list)
        config = self.env['ir.config_parameter'].sudo()
        multiple_discounts_purchase = config.get_param('purchase.enable_multiple_discounts') in ('1', 'true', 'True')
        qtd = config.get_param('purchase.enable_multiple_discounts_qtd', 'due')
        show_discount3 = (qtd == 'due')

        # Campos temporários em memória
        res['show_multiple_discounts_purchase'] = multiple_discounts_purchase
        res['show_discount3_purchase'] = show_discount3
        return res

    show_multiple_discounts_purchase = fields.Boolean(store=False)
    show_discount3_purchase = fields.Boolean(store=False)

