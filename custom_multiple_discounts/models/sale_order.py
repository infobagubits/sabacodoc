from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    
    
    show_discount3 = fields.Boolean(
        compute='_compute_show_discount3',
        store=False
    )

    @api.depends('order_line')
    def _compute_show_discount3(self):
        config_param = self.env['ir.config_parameter'].sudo()
        qtd = config_param.get_param('sale.enable_multiple_discounts_qtd', 'due')

        for order in self:
            order.show_discount3 = (qtd == 'due')  # ou 'due' dependendo de como você nomeou as opções
    
    
    
    def action_open_discount_wizard(self):
        self.ensure_one()

        # Lê o parâmetro de configuração
        enable_multiple = self.env['ir.config_parameter'].sudo().get_param('sale.enable_multiple_discounts', 'False') in ('1', 'true', 'True')

        return {
            'name': 'Discount',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.discount',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'hide_discount': enable_multiple,
                'default_discount_type': 'so_discount' if enable_multiple else 'sol_discount',  # 👈 Aqui está a mágica
            }
        }
    
    show_multiple_discounts = fields.Boolean(
        compute="_compute_show_multiple_discounts",
        store=False
    )
    
    show_discount_field = fields.Boolean(
        compute="_compute_show_discount_field",
        store=False
    )

    @api.depends()
    def _compute_show_multiple_discounts(self):
        config = self.env['ir.config_parameter'].sudo().get_param('sale.enable_multiple_discounts', 'False')
        is_enabled = config in ('True', '1', 'true')
        for order in self:
            order.show_multiple_discounts = is_enabled
            
    @api.depends()
    def _compute_show_discount_field(self):
        """Verifica se o grupo de descontos por linha está habilitado"""
        group = self.env.ref('sale.group_discount_per_so_line')
        for order in self:
            order.show_discount_field = group in self.env.user.groups_id   
    
    @api.model
    def default_get(self, fields_list):
        """Força o contexto a carregar os valores na criação do pedido"""
        res = super().default_get(fields_list)
        config = self.env['ir.config_parameter'].sudo()
        multiple_discounts = config.get_param('sale.enable_multiple_discounts') in ('1', 'true', 'True')
        show_discount_field = self.env.ref('sale.group_discount_per_so_line') in self.env.user.groups_id

        # Campos temporários em memória
        res['show_multiple_discounts'] = multiple_discounts
        res['show_discount_field'] = show_discount_field
        return res

    show_multiple_discounts = fields.Boolean(store=False)
    show_discount_field = fields.Boolean(store=False)