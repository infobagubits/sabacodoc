from odoo import models, fields, api

class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    discount1 = fields.Float(string="Discount 1 (%)", default=0.0)
    discount2 = fields.Float(string="Discount 2 (%)", default=0.0)
    discount3 = fields.Float(string="Discount 3 (%)", default=0.0)

    # Field that controls visibility
    multiple_discounts_enabled = fields.Boolean(
        string="Multiple Discounts Enabled",
        compute="_compute_multiple_discounts_enabled",
        store=False
    )

    # Field that controls quantity
    multiple_discounts_enabled_qtd = fields.Boolean(
        string="Multiple Discounts Enabled Qtd",
        compute="_compute_multiple_discounts_enabled_qtd",
        store=False
    )

    @api.depends()
    def _compute_multiple_discounts_enabled_qtd(self):
        qtd_value = self.env['ir.config_parameter'].sudo().get_param('purchase.enable_multiple_discounts_qtd', 'due')
        for line in self:
            line.multiple_discounts_enabled_qtd = (qtd_value == 'due')
        
    @api.depends()
    def _compute_multiple_discounts_enabled(self):
        param_value = self.env['ir.config_parameter'].sudo().get_param('purchase.enable_multiple_discounts', 'False')
        is_enabled = param_value in ('True', '1', 'true')
        for line in self:
            line.multiple_discounts_enabled = is_enabled

