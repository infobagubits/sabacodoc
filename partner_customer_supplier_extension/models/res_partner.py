from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean(string="E' un cliente")
    is_supplier = fields.Boolean(
        string="E' un fornitore",
        help="Se questo partner è un fornitore, verrà mostrata la scheda Prodotti"
    )

    # Campos para a aba Prodotti
    supplier_product_ids = fields.One2many(
        'product.supplierinfo',
        'partner_id',
        string='Prodotti del Fornitore',
        help='Prodotti dove questo partner è fornitore'
    )
