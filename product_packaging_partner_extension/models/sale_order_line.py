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
        1. PRIMA: Verifica se embalagem tem flag sales = True
        2. SEGUNDA: Se c'è un cliente e imballaggi collegati: solo imballaggi del cliente
        3. TERZA: Altrimenti: tutti gli imballaggi di vendita del prodotto
        """
        for line in self:
            if not line.product_id:
                line.available_packaging_ids = [(5, 0, 0)]  # Rimuove tutti
                continue
            
            # Cerca tutti gli imballaggi del prodotto che sono per VENDITE
            all_sales_packagings = self.env['product.packaging'].search([
                ('product_id', '=', line.product_id.id),
                ('sales', '=', True)  # SOLO embalagens de vendas
            ])
            
            # Se c'è un cliente selezionato
            if line.order_id.partner_id:
                # Cerca imballaggi collegati a questo cliente (che siano per vendite)
                # IMPORTANTE: Considera apenas parceiros que são CLIENTES
                partner_packagings = all_sales_packagings.filtered(
                    lambda p: line.order_id.partner_id.id in p.contact_line_ids.filtered(
                        lambda c: c.partner_id.is_customer
                    ).partner_id.ids
                )
                
                if partner_packagings:
                    # PRIORITÀ: Se esistono imballaggi collegati al cliente, mostra solo quelli
                    line.available_packaging_ids = [(6, 0, partner_packagings.ids)]
                else:
                    # FALLBACK: Se non ci sono imballaggi collegati al cliente, mostra solo quelli SENZA CLIENTE
                    no_customer_packagings = all_sales_packagings.filtered(
                        lambda p: not p.contact_line_ids.filtered(lambda c: c.partner_id.is_customer)
                    )
                    line.available_packaging_ids = [(6, 0, no_customer_packagings.ids)]
            else:
                # Se non c'è un cliente, mostra solo gli imballaggi senza cliente
                no_customer_packagings = all_sales_packagings.filtered(
                    lambda p: not p.contact_line_ids.filtered(lambda c: c.partner_id.is_customer)
                )
                line.available_packaging_ids = [(6, 0, no_customer_packagings.ids)] 