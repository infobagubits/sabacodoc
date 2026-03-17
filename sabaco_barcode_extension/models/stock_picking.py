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

    # Totais no popup barcode (quantità ricevute)
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Valuta', readonly=True)
    totale_imponibile_barcode = fields.Monetary(
        string='Totale imponibile',
        compute='_compute_totals_barcode',
        currency_field='currency_id',
        help='Somma (quantità ricevuta × prezzo) per le righe del trasferimento.')
    iva_barcode = fields.Monetary(
        string='Iva',
        compute='_compute_totals_barcode',
        currency_field='currency_id',
        help='Iva calcolata sulle quantità ricevute (da ordine di acquisto se presente).')
    totale_ivato_barcode = fields.Monetary(
        string='Totale ivato',
        compute='_compute_totals_barcode',
        currency_field='currency_id',
        help='Totale imponibile + Iva (quantità ricevute).')

    def _get_fields_stock_barcode(self):
        """Estende i campi inviati al client barcode per includere origin, documento fornitore e totali."""
        fields = super()._get_fields_stock_barcode()
        fields.append('origin')
        fields.append('supplier_document_number')
        fields.append('supplier_document_date')
        fields.append('totale_imponibile_barcode')
        fields.append('iva_barcode')
        fields.append('totale_ivato_barcode')
        fields.append('currency_id')
        fields.append('l10n_it_show_print_ddt_button')
        return fields

    @api.depends('move_ids', 'move_ids.quantity', 'move_ids.price_unit', 'move_ids.purchase_line_id', 'move_ids.purchase_line_id.taxes_id')
    def _compute_totals_barcode(self):
        """Totale imponibile, Iva e Totale ivato in base alle quantità ricevute (move.quantity)."""
        for picking in self:
            totale_imponibile = 0.0
            totale_iva = 0.0
            totale_ivato = 0.0
            currency = picking.company_id.currency_id
            for move in picking.move_ids:
                qty = move.quantity
                if not qty:
                    continue 
                price_unit = move.price_unit or 0.0
                if move.purchase_line_id and move.purchase_line_id.taxes_id:
                    tax_res = move.purchase_line_id.taxes_id.compute_all(
                        price_unit,
                        currency=currency,
                        quantity=qty,
                        product=move.product_id,
                        partner=picking.partner_id,
                    )
                    totale_imponibile += tax_res['total_excluded']
                    totale_iva += tax_res['total_included'] - tax_res['total_excluded']
                    totale_ivato += tax_res['total_included']
                else:
                    subtotal = qty * price_unit
                    totale_imponibile += subtotal
                    totale_ivato += subtotal
            picking.totale_imponibile_barcode = totale_imponibile
            picking.iva_barcode = totale_iva
            picking.totale_ivato_barcode = totale_ivato

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

    def action_assign(self):
        """Se chiamato dal popup barcode (context from_barcode_form), dopo la riserva
        restituisce l'azione cliente per riaprire lo stesso picking nel barcode, così
        i dati (quantità riservate) si aggiornano senza uscire e rientrare."""
        result = super().action_assign()
        if self.env.context.get('from_barcode_form') and len(self) == 1:
            return {
                'type': 'ir.actions.client',
                'tag': 'stock_barcode_client_action',
                'res_model': 'stock.picking',
                'context': {'active_id': self.id},
            }
        return result

