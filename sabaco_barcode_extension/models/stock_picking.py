# -*- coding: utf-8 -*-

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    purchase_order_note = fields.Html(
        string='Purchase Order Note',
        compute='_compute_purchase_order_note',
        store=False,
        help='Note from the related Purchase Order based on origin field'
    )

    def _get_fields_stock_barcode(self):
        """Estende i campi inviati al client barcode per includere origin e documento fornitore"""
        fields = super()._get_fields_stock_barcode()
        fields.append('origin')
        fields.append('supplier_document_number')
        fields.append('supplier_document_date')
        return fields

    @api.depends('origin')
    def _compute_purchase_order_note(self):
        """Compute the note from purchase.order based on origin field"""
        for picking in self:
            if picking.origin:
                # Busca a purchase.order pelo nome (campo name) que corresponde ao origin
                purchase_order = self.env['purchase.order'].search([
                    ('name', '=', picking.origin)
                ], limit=1)
                
                if purchase_order and purchase_order.x_studio_note:
                    picking.purchase_order_note = purchase_order.x_studio_note
                else:
                    picking.purchase_order_note = False
            else:
                picking.purchase_order_note = False

