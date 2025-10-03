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

    @api.depends('product_id', 'product_qty', 'product_uom', 'company_id', 'order_id.partner_id', 'order_id.date_order')
    def _compute_price_unit_and_date_planned_and_name(self):
        """
        Extends the native method to also fetch discount1, discount2, discount3
        from product.supplierinfo when the product and vendor are selected
        """
        # Call the parent method to maintain standard behavior
        res = super()._compute_price_unit_and_date_planned_and_name()
        
        # Now also populate discount1, discount2, discount3 from supplierinfo
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id:
                continue
                
            # Get the seller (same logic as native Odoo)
            params = line._get_select_sellers_params()
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
                uom_id=line.product_uom,
                params=params
            )
            
            # If seller found, apply discount1, discount2, discount3
            if seller:
                line.discount1 = seller.discount1 or 0.0
                line.discount2 = seller.discount2 or 0.0
                line.discount3 = seller.discount3 or 0.0
            else:
                # If no seller, reset discounts
                line.discount1 = 0.0
                line.discount2 = 0.0
                line.discount3 = 0.0
        
        return res

