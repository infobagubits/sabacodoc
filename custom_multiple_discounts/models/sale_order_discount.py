# Necessary imports from Odoo and auxiliary libraries
from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_repr
from collections import defaultdict

# Defines the transient model (wizard) for applying discounts
class SaleOrderDiscount(models.TransientModel):
    _name = 'sale.order.discount'  # Technical name of the model
    _description = "Discount Wizard"  # Model description

    # Field that stores the linked sale order
    sale_order_id = fields.Many2one(
        'sale.order',
        default=lambda self: self.env.context.get('active_id'),
        required=True
    )

    # Company linked to the sale order (related field)
    company_id = fields.Many2one(related='sale_order_id.company_id')

    # Sale order currency (related field)
    currency_id = fields.Many2one(related='sale_order_id.currency_id')

    # Fixed discount amount (in currency)
    discount_amount = fields.Monetary(string="Amount")

    # Discount percentage
    discount_percentage = fields.Float(string="Percentage")

    # Type of discount applied (radio button)
    discount_type = fields.Selection(
        selection=lambda self: self._get_discount_type_selection(),  # Dynamically generated options
        default='sol_discount',  # Default: per line discount
        string="Discount Type"
    )

    # Taxes applicable to the discount line
    tax_ids = fields.Many2many(
        string="Taxes",
        help="Taxes to add on the discount line.",
        comodel_name='account.tax',
        domain="[('type_tax_use', '=', 'sale'), ('company_id', '=', company_id)]",
    )

    @api.model
    def _get_discount_type_selection(self):
        """
        Dynamically defines the options for the 'discount_type' field
        Removes the 'On All Order Lines' option if multiple discounts are enabled
        """
        param = self.env['ir.config_parameter'].sudo().get_param('sale.enable_multiple_discounts', 'False')
        multiple_enabled = param in ['1', 'true', 'True']

        # Default options
        options = [
            ('so_discount', "Global Discount"),
            ('amount', "Fixed Amount"),
        ]

        # Adds the 'sol_discount' option only if multiple discounts are disabled
        if not multiple_enabled:
            options.insert(0, ('sol_discount', "On All Order Lines"))

        return options

    @api.constrains('discount_type', 'discount_percentage')
    def _check_discount_amount(self):
        """
        Prevents invalid percentage values from being applied
        """
        for wizard in self:
            if (
                wizard.discount_type in ('sol_discount', 'so_discount') and
                wizard.discount_percentage > 1.0
            ):
                raise ValidationError(_("Invalid discount amount"))

    def _prepare_discount_product_values(self):
        """
        Defines the default values for the discount product
        """
        self.ensure_one()
        return {
            'name': _('Discount'),
            'type': 'service',
            'invoice_policy': 'order',
            'list_price': 0.0,
            'company_id': self.company_id.id,
            'taxes_id': None,
        }

    def _prepare_discount_line_values(self, product, amount, taxes, description=None):
        """
        Prepares the values for creating a discount line in the order
        """
        self.ensure_one()
        vals = {
            'order_id': self.sale_order_id.id,
            'product_id': product.id,
            'sequence': 999,
            'price_unit': -amount,
            'tax_id': [Command.set(taxes.ids)],
        }
        if description:
            vals['name'] = description
        return vals

    def _get_discount_product(self):
        """
        Obtains (or creates, if necessary) the product used for the discount line
        """
        self.ensure_one()
        discount_product = self.company_id.sale_discount_product_id
        if not discount_product:
            # Checks permissions to create the discount product
            if (
                self.env['product.product'].has_access('create') and
                self.company_id.has_access('write') and
                self.company_id._filtered_access('write') and
                self.company_id.check_field_access_rights('write', ['sale_discount_product_id'])
            ):
                # Creates the product
                self.company_id.sale_discount_product_id = self.env['product.product'].create(
                    self._prepare_discount_product_values()
                )
            else:
                # Prevents execution if it cannot create the product
                raise ValidationError(_(
                    "There does not seem to be any discount product configured for this company yet."
                ))
            discount_product = self.company_id.sale_discount_product_id
        return discount_product

    def _create_discount_lines(self):
        """
        Creates one or more discount lines on the sale order, according to the wizard configuration
        """
        self.ensure_one()
        discount_product = self._get_discount_product()

        # Calculates the discount percentage based on the fixed or percentage value
        if self.discount_type == 'amount':
            if not self.sale_order_id.amount_total:
                return
            discount_percentage = self.discount_amount / self.sale_order_id.amount_total
        else:
            discount_percentage = self.discount_percentage

        # Groups prices by tax group
        total_price_per_tax_groups = defaultdict(float)
        for line in self.sale_order_id.order_line:
            if not line.product_uom_qty or not line.price_unit:
                continue
            discounted_price = line.price_unit * (1 - (line.discount or 0.0)/100)
            total_price_per_tax_groups[line.tax_id] += discounted_price * line.product_uom_qty

        # Decimal precision configured for discounts
        discount_dp = self.env['decimal.precision'].precision_get('Discount')
        if not total_price_per_tax_groups:
            return  # Nothing to apply

        # If all taxes are the same, create a single discount line
        if len(total_price_per_tax_groups) == 1:
            taxes = next(iter(total_price_per_tax_groups.keys()))
            subtotal = total_price_per_tax_groups[taxes]
            vals_list = [self._prepare_discount_line_values(
                product=discount_product,
                amount=subtotal * discount_percentage,
                taxes=taxes,
                description=_("Discount %(percent)s%%", percent=float_repr(discount_percentage * 100, discount_dp))
            )]
        else:
            # If there is more than one tax group, create one line for each
            vals_list = [
                self._prepare_discount_line_values(
                    product=discount_product,
                    amount=subtotal * discount_percentage,
                    taxes=taxes,
                    description=_(
                        "Discount %(percent)s%% - On products with taxes: %(taxes)s",
                        percent=float_repr(discount_percentage * 100, discount_dp),
                        taxes=", ".join(taxes.mapped('name'))
                    )
                ) for taxes, subtotal in total_price_per_tax_groups.items()
            ]

        # Creates the lines in the sale order
        return self.env['sale.order.line'].create(vals_list)

    def action_apply_discount(self):
        """
        Applies the discount to the sale order according to the selected type
        """
        self.ensure_one()
        self = self.with_company(self.company_id)

        # Discount applied to all order lines (native Odoo)
        if self.discount_type == 'sol_discount':
            self.sale_order_id.order_line.write({'discount': self.discount_percentage * 100})
        else:
            # Discount as a product line (by value or global)
            self._create_discount_lines()
