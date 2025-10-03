from odoo import models, fields, api

class PurchaseConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_multiple_discounts_purchase = fields.Boolean(
        string="Multiple Discounts for Purchase",
        config_parameter='purchase.enable_multiple_discounts',
        help="When checked, it hides the default discount field and shows discount1, 2, 3 on the purchase order lines."
    )
    
    enable_multiple_discounts_purchase_qtd = fields.Selection([
        ('due', '2 discounts'),
        ('tre', '3 discounts')
    ], string="Multiple Discounts Quantity for Purchase",
       config_parameter='purchase.enable_multiple_discounts_qtd',
       default='due',
       help="Defines how many multiple discount fields will be shown on the purchase order lines.")

    @api.model
    def set_values(self):
        # Previous value
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        old_value = IrConfigParam.get_param('purchase.enable_multiple_discounts', 'False')
        super(PurchaseConfigSettings, self).set_values()
        # New value
        new_value = IrConfigParam.get_param('purchase.enable_multiple_discounts', 'False')

        old_bool = old_value in ('True', '1', 'true')
        new_bool = new_value in ('True', '1', 'true')

        # If the user unchecked it, we reset discount1, discount2, discount3
        if old_bool and not new_bool:
            lines = self.env['purchase.order.line'].search([])
            lines.write({
                'discount1': 0.0,
                'discount2': 0.0,
                'discount3': 0.0,
            })

