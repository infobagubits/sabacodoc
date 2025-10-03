# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Sovrascrive il campo type per cambiare "Consumabile" in "Prodotto"
    type = fields.Selection(
        selection=[
            ('consu', "Prodotto"),
            ('service', "Service"),
            ('combo', "Combo"),
        ],
        string="Product Type",
        required=True,
        default='consu',
    )

