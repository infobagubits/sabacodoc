from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    available_packaging_ids = fields.Many2many(
        'product.packaging',
        compute='_compute_available_packaging_ids',
        string='Imballaggi Disponibili'
    )

    @api.depends('product_id', 'order_id.partner_id')
    def _compute_available_packaging_ids(self):
        """
        Calcola gli imballaggi disponibili basato sul fornitore:
        1. PRIMA: Verifica se embalagem tem flag purchase = True
        2. SEGUNDA: Se c'è un fornitore e imballaggi collegati: solo imballaggi del fornitore
        3. TERZA: Altrimenti: tutti gli imballaggi di acquisto del prodotto
        """
        for line in self:
            if not line.product_id:
                line.available_packaging_ids = [(5, 0, 0)]  # Rimuove tutti
                continue
            
            # Cerca tutti gli imballaggi del prodotto che sono per ACQUISTI
            all_purchase_packagings = self.env['product.packaging'].search([
                ('product_id', '=', line.product_id.id),
                ('purchase', '=', True)  # SOLO embalagens de compras
            ])
            
            # Se c'è un fornitore selezionato
            if line.order_id.partner_id:
                # Cerca imballaggi collegati a questo fornitore (che siano per acquisti)
                # IMPORTANTE: Considera apenas parceiros que são FORNECEDORES
                partner_packagings = all_purchase_packagings.filtered(
                    lambda p: line.order_id.partner_id.id in p.contact_line_ids.filtered(
                        lambda c: c.partner_id.is_supplier
                    ).partner_id.ids
                )
                
                if partner_packagings:
                    # PRIORITÀ: Se esistono imballaggi collegati al fornitore, mostra solo quelli
                    line.available_packaging_ids = [(6, 0, partner_packagings.ids)]
                else:
                    # FALLBACK: Se non ci sono imballaggi collegati al fornitore, mostra solo quelli SENZA FORNITORE
                    no_supplier_packagings = all_purchase_packagings.filtered(
                        lambda p: not p.contact_line_ids.filtered(lambda c: c.partner_id.is_supplier)
                    )
                    line.available_packaging_ids = [(6, 0, no_supplier_packagings.ids)]
            else:
                # Se non c'è un fornitore, mostra solo gli imballaggi senza fornitore
                no_supplier_packagings = all_purchase_packagings.filtered(
                    lambda p: not p.contact_line_ids.filtered(lambda c: c.partner_id.is_supplier)
                )
                line.available_packaging_ids = [(6, 0, no_supplier_packagings.ids)] 