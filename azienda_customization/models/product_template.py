# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _selection_type(self):
        return [
            ('consu', 'Prodotto'),
            ('service', 'Servizio'),
            ('combo', 'Combo'),
        ]

    # Sovrascrive il campo type per cambiare "Consumabile" in "Prodotto"
    type = fields.Selection(
        selection='_selection_type',
        string="Tipologia prodotto",
        required=True,
        default='consu',
    )

