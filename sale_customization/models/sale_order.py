from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_id_auto_products(self):
        """
        Quando il cliente viene selezionato, modificato o rimosso:
        - Se cliente selezionato: cerca gli ultimi 4 prodotti venduti e crea righe automatiche
        - Se cliente modificato: pulisce righe esistenti e crea nuove con prodotti del nuovo cliente  
        - Se cliente rimosso: pulisce tutte le righe di prodotti
        """
        # Pulire sempre prima le righe esistenti
        self.order_line = [(5, 0, 0)]  # Rimuove tutte le righe
        
        # Se non c'è cliente selezionato, pulire e uscire
        if not self.partner_id:
            _logger.info("Cliente rimosso - tutte le righe di prodotti sono state pulite")
            return
        
        # Prendi gli ultimi 4 ordini confermati del cliente (escludendo l'attuale)
        confirmed_orders = self.env['sale.order'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['sale', 'done']),
            ('id', '!=', self.id or 0)
        ], order='date_order desc', limit=4)

        if not confirmed_orders:
            _logger.info(f"Nessun ordine precedente trovato per il cliente {self.partner_id.name}")
            return

        # Raccogli tutte le righe prodotto (anche ripetute) degli ultimi 4 ordini
        order_lines = []
        added_product_ids = set()
        for order in confirmed_orders:
            for line in order.order_line.filtered(lambda l: l.product_id and not l.display_type and l.product_uom_qty > 0):
                product = line.product_id
                if product.exists() and product.sale_ok and product.id not in added_product_ids:
                    secondary_uom_id = False
                    secondary_qty = 0.0
                    if hasattr(product.product_tmpl_id, 'x_secondary_uom_id') and product.product_tmpl_id.x_secondary_uom_id:
                        secondary_uom_id = product.product_tmpl_id.x_secondary_uom_id.id
                    line_vals = {
                        'product_id': product.id,
                        'product_uom_qty': 0.0,  # Quantità sempre 0
                        'product_uom': product.uom_id.id,
                        'price_unit': product.list_price,
                        'name': product.display_name,
                    }
                    if secondary_uom_id:
                        line_vals.update({
                            'x_secondary_qty': secondary_qty,
                            'x_secondary_uom_id': secondary_uom_id,
                        })
                    order_lines.append((0, 0, line_vals))
                    added_product_ids.add(product.id)

        if order_lines:
            self.order_line = order_lines
            _logger.info(f"Create {len(order_lines)} righe automatiche con tutti i prodotti degli ultimi 4 ordini per il cliente {self.partner_id.name}")
        else:
            _logger.info(f"Nessuna riga valida creata per il cliente {self.partner_id.name}")