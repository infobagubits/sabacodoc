# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Unità di misura secondaria (correlata al prodotto)
    x_secondary_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unità Secondaria',
        related='product_id.x_secondary_uom_id',
        store=True,
        readonly=True
    )

    # Quantità nell'unità secondaria (inserita manualmente)
    x_secondary_qty = fields.Float(
        string='Quantità Secondaria',
        help='Quantità nella unità di misura secondaria'
    )

    # Indica se il prodotto ha unità secondaria attiva
    x_secondary_active = fields.Boolean(
        string="Unità Secondaria Attiva",
        related='product_id.x_secondary_uom_id.active',
        store=True,
        readonly=True
    ) 