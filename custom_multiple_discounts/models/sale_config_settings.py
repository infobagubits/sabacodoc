from odoo import models, fields, api

class SaleConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_multiple_discounts = fields.Boolean(
        string="Multiple Discounts",
        config_parameter='sale.enable_multiple_discounts',
        help="When checked, it hides the default discount field and shows discount1, 2, 3 on the sale lines."
    )
    
    enable_multiple_discounts_qtd = fields.Selection([
        ('due', '2 discounts'),
        ('tre', '3 discounts')
    ], string="Multiple Discounts Quantity",
       config_parameter='sale.enable_multiple_discounts_qtd',
       default='due',
       help="Defines how many multiple discount fields will be shown on the sale order lines.")

    @api.model
    def set_values(self):
        # Previous value
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        old_value = IrConfigParam.get_param('sale.enable_multiple_discounts', 'False')
        super(SaleConfigSettings, self).set_values()
        # New value
        new_value = IrConfigParam.get_param('sale.enable_multiple_discounts', 'False')

        old_bool = old_value in ('True', '1', 'true')
        new_bool = new_value in ('True', '1', 'true')

        # If the user unchecked it, we reset discount1, discount2, discount3
        if old_bool and not new_bool:
            lines = self.env['sale.order.line'].search([])
            lines.write({
                'discount1': 0.0,
                'discount2': 0.0,
                'discount3': 0.0,
            })
