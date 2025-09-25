from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    available_packaging_ids = fields.Many2many(
        'product.packaging',
        compute='_compute_available_packaging_ids',
        string='Imballaggi Disponibili'
    )

    @api.depends('product_id', 'order_id.partner_id')
    def _compute_available_packaging_ids(self):
        """
        Calcola gli imballaggi disponibili basato sul cliente:
        - Se c'è un cliente e imballaggi collegati: solo imballaggi del cliente
        - Altrimenti: tutti gli imballaggi del prodotto
        """
        for line in self:
            if not line.product_id:
                line.available_packaging_ids = [(5, 0, 0)]  # Rimuove tutti
                continue
            
            # Cerca tutti gli imballaggi del prodotto
            all_packagings = self.env['product.packaging'].search([
                ('product_id', '=', line.product_id.id)
            ])
            
            # Se c'è un cliente selezionato
            if line.order_id.partner_id:
                # Cerca imballaggi collegati a questo cliente
                partner_packagings = all_packagings.filtered(
                    lambda p: line.order_id.partner_id.id in p.contact_line_ids.partner_id.ids
                )
                
                if partner_packagings:
                    # Se esistono imballaggi collegati, mostra solo quelli
                    line.available_packaging_ids = [(6, 0, partner_packagings.ids)]
                else:
                    # Se non ci sono imballaggi collegati, mostra tutti
                    line.available_packaging_ids = [(6, 0, all_packagings.ids)]
            else:
                # Se non c'è un cliente, mostra tutti
                line.available_packaging_ids = [(6, 0, all_packagings.ids)] 