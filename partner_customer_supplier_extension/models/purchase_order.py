from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    contact_partner_id = fields.Many2one(
        'res.partner',
        string='Contatto'
    )

    def _get_domain_product_id(self):
        domain = [('purchase_ok', '=', True)]
        config = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
        if config == 'True' and self.order_id.partner_id:
            supplier_info = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.order_id.partner_id.id)
            ])
            if supplier_info:
                product_templates = supplier_info.mapped('product_tmpl_id')
                domain += [('product_tmpl_id', 'in', product_templates.ids)]
            else:
                # Retorna domínio vazio quando não houver produtos vinculados
                return [('id', '=', False)]
        return domain

    product_id = fields.Many2one(
        domain=lambda self: self._get_domain_product_id()
    )

    @api.onchange('contact_partner_id')
    def _onchange_contact_partner_id(self):
        domain = []
        config = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
        if config == 'True' and self.contact_partner_id:
            # Busca produtos vinculados ao fornecedor selecionado
            supplier_info = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.contact_partner_id.id)
            ])
            product_templates = supplier_info.mapped('product_tmpl_id')
            products = self.env['product.product'].search([
                ('product_tmpl_id', 'in', product_templates.ids)
            ])
            
            domain = [('id', 'in', products.ids)]
            self.name = self.contact_partner_id.name
            self.price_unit = 0.0
            
            # Se não houver produtos vinculados, limpa o campo produto
            if not products:
                self.product_id = False

        return {
            'domain': {
                'product_id': domain
            }
        }

    @api.onchange('order_id.partner_id')
    def _onchange_order_partner_id(self):
        domain = []
        config = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
        if config == 'True' and self.order_id.partner_id:
            supplier_info = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.order_id.partner_id.id)
            ])
            product_templates = supplier_info.mapped('product_tmpl_id')
            domain = [('product_tmpl_id', 'in', product_templates.ids)]
        
        return {'domain': {'product_id': domain}}

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super(PurchaseOrderLine, self).onchange_product_id()
        
        config = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
        if config == 'True' and self.order_id.partner_id:
            # Busca produtos vinculados ao fornecedor na aba Acquisti
            supplier_info = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.order_id.partner_id.id)
            ])
            product_templates = supplier_info.mapped('product_tmpl_id')
            
            # Retorna o domínio para filtrar produtos
            return {
                'domain': {
                    'product_id': [
                        ('purchase_ok', '=', True),
                        ('product_tmpl_id', 'in', product_templates.ids)
                    ]
                }
            }
        return result

    def _get_filtered_products(self):
        config = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
        if config == 'True' and self.order_id.partner_id:
            # Busca produtos vinculados ao fornecedor na aba Acquisti
            supplier_info = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.order_id.partner_id.id)
            ])
            product_templates = supplier_info.mapped('product_tmpl_id')
            products = self.env['product.product'].search([
                ('product_tmpl_id', 'in', product_templates.ids)
            ])
            return products.ids
        return []

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        config = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
        if config == 'True' and self.env.context.get('default_order_id'):
            order = self.env['purchase.order'].browse(self.env.context['default_order_id'])
            if order.partner_id:
                supplier_info = self.env['product.supplierinfo'].search([
                    ('partner_id', '=', order.partner_id.id)
                ])
                product_templates = supplier_info.mapped('product_tmpl_id')
                res['domain'] = {'product_id': [('product_tmpl_id', 'in', product_templates.ids)]}
        return res

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    available_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_available_products',
        string='Available Products'
    )

    @api.depends('partner_id')
    def _compute_available_products(self):
        for order in self:
            config = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
            
            if config == 'True' and order.partner_id:
                supplier_info = self.env['product.supplierinfo'].search([
                    ('partner_id', '=', order.partner_id.id)
                ])
                if supplier_info:
                    product_templates = supplier_info.mapped('product_tmpl_id')
                    products = self.env['product.product'].search([
                        ('purchase_ok', '=', True),
                        ('product_tmpl_id', 'in', product_templates.ids)
                    ])
                    order.available_product_ids = products
                else:
                    # Retorna lista vazia quando não houver produtos vinculados
                    order.available_product_ids = self.env['product.product']
            else:
                order.available_product_ids = self.env['product.product'].search([('purchase_ok', '=', True)])

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        result = super(PurchaseOrder, self).onchange_partner_id()
        
        config = self.env['ir.config_parameter'].sudo().get_param('purchase.use_product_filter', 'False')
        if config == 'True' and self.partner_id:
            # Busca produtos vinculados ao fornecedor
            supplier_info = self.env['product.supplierinfo'].search([
                ('partner_id', '=', self.partner_id.id)
            ])
            product_templates = supplier_info.mapped('product_tmpl_id')
            
            # Limpa produtos que não pertencem ao fornecedor
            for line in self.order_line:
                if line.product_id and line.product_id.product_tmpl_id not in product_templates:
                    line.product_id = False
        
        return result 