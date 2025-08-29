from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

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
        - Se c'è un fornitore e imballaggi collegati: solo imballaggi del fornitore
        - Altrimenti: tutti gli imballaggi del prodotto
        - Con trattamento di errore robusto per prodotti senza imballaggi
        """
        for line in self:
            try:
                if not line.product_id:
                    line.available_packaging_ids = [(5, 0, 0)]  # Rimuove tutti
                    continue
                
                # Cerca tutti gli imballaggi del prodotto
                all_packagings = self.env['product.packaging'].search([
                    ('product_id', '=', line.product_id.id)
                ])
                
                # Se c'è un fornitore selezionato
                if line.order_id.partner_id:
                    # Cerca imballaggi collegati a questo fornitore
                    partner_packagings = all_packagings.filtered(
                        lambda p: line.order_id.partner_id.id in p.contact_line_ids.partner_id.ids or not p.contact_line_ids.partner_id.ids
                    )
                    
                    if partner_packagings:
                        # Se esistono imballaggi collegati, mostra solo quelli
                        line.available_packaging_ids = [(6, 0, partner_packagings.ids)]
                    else:
                        # Se non ci sono imballaggi collegati al fornitore, mostra tutti
                        line.available_packaging_ids = [(6, 0, all_packagings.ids)]
                else:
                    # Se non c'è fornitore, mostra tutti gli imballaggi del prodotto
                    line.available_packaging_ids = [(6, 0, all_packagings.ids)]
                    
            except ValueError as ve:
                # Tratamento específico para ValueError (produtos sem embalagens)
                line.available_packaging_ids = [(5, 0, 0)]
                _logger.info(f"Produto {line.product_id.name if line.product_id else 'N/A'} sem embalagens - definindo lista vazia: {ve}")
                
            except Exception as e:
                # Tratamento para outros erros inesperados
                line.available_packaging_ids = [(5, 0, 0)]
                _logger.warning(f"Erro inesperado ao computar embalagens para produto {line.product_id.name if line.product_id else 'N/A'}: {e}")
                
            # Garantir que sempre tenha um valor válido
            if not line.available_packaging_ids:
                line.available_packaging_ids = [(5, 0, 0)]