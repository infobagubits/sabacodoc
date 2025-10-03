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
    
    @api.depends('discount1', 'discount2', 'discount3')
    def _compute_discount(self):
        """
        Override native discount field computation to calculate from multiple discounts in cascade.
        This method is called BEFORE _compute_amount, ensuring discount is ready for subtotal calculation.
        """
        param_value = self.env['ir.config_parameter'].sudo().get_param('purchase.enable_multiple_discounts', 'False')
        is_enabled = param_value in ('True', '1', 'true')
        
        for line in self:
            if is_enabled and (line.discount1 or line.discount2 or line.discount3):
                d1 = line.discount1 or 0.0
                d2 = line.discount2 or 0.0
                d3 = line.discount3 or 0.0
                # Cascade calculation
                multiplicador = (1 - d1/100.0) * (1 - d2/100.0) * (1 - d3/100.0)
                line.discount = (1.0 - multiplicador) * 100.0
            elif not is_enabled:
                # If feature is disabled, keep discount as is (don't override)
                pass
    
    # Override the native _compute_amount to ensure our discount is used
    @api.depends('product_qty', 'price_unit', 'taxes_id', 'discount', 'discount1', 'discount2', 'discount3')
    def _compute_amount(self):
        """
        Extend native method to ensure discount is recalculated from discount1/2/3 before computing subtotal.
        """
        # First, ensure discount is up to date from discount1/2/3
        self._compute_discount()
        # Then call the parent method to compute price_subtotal, price_total, price_tax
        return super()._compute_amount()

    @api.onchange('discount1', 'discount2', 'discount3', 'product_qty', 'price_unit')
    def _onchange_multiple_discounts(self):
        """
        When the user fills discount1, discount2, discount3, or changes quantity/price,
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

