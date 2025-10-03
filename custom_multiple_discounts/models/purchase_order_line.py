from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

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

    @api.onchange('discount1', 'discount2', 'discount3')
    def _onchange_multiple_discounts(self):
        """
        When the user fills discount1, discount2, discount3,
        we calculate the TOTAL DISCOUNT in cascade and assign it to 'discount' (native Odoo).
        Cascade example:
           final_price = base_price * (1 - d1/100) * (1 - d2/100) * (1 - d3/100)
           discount_total(%) = 1 - [(1 - d1/100)*(1 - d2/100)*(1 - d3/100)]
        """
        param_value = self.env['ir.config_parameter'].sudo().get_param('purchase.enable_multiple_discounts', 'False')
        is_enabled = param_value in ('True', '1', 'true')

        if is_enabled:
            d1 = self.discount1 or 0.0
            d2 = self.discount2 or 0.0
            d3 = self.discount3 or 0.0
            # Cascade calculation
            multiplicador = (1 - d1/100.0) * (1 - d2/100.0) * (1 - d3/100.0)
            discount_total = (1.0 - multiplicador) * 100.0
            # Assign this value to the native Odoo `discount` field
            self.discount = discount_total
        else:
            # If the feature is disabled, reset the 3 fields
            self.discount1 = 0.0
            self.discount2 = 0.0
            self.discount3 = 0.0

    @api.onchange('product_id')
    def _onchange_product_id_discounts(self):
        """
        When product is selected, automatically fetch discount1, discount2, discount3
        from product.supplierinfo. This runs AFTER the native onchange_product_id
        """
        if not self.product_id:
            self.discount1 = 0.0
            self.discount2 = 0.0
            self.discount3 = 0.0
            return
            
        # Get the seller using the same logic as Odoo uses for price
        params = self._get_select_sellers_params()
        seller = self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty or 1.0,
            date=self.order_id.date_order and self.order_id.date_order.date() or fields.Date.context_today(self),
            uom_id=self.product_uom or self.product_id.uom_po_id,
            params=params
        )
        
        # If seller found, apply discount1, discount2, discount3
        if seller:
            self.discount1 = seller.discount1 or 0.0
            self.discount2 = seller.discount2 or 0.0
            self.discount3 = seller.discount3 or 0.0
        else:
            # If no seller, reset discounts
            self.discount1 = 0.0
            self.discount2 = 0.0
            self.discount3 = 0.0

