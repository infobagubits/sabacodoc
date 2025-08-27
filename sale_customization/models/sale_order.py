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
        
        # Prima cercare gli ordini confermati del cliente ordinati per data
        confirmed_orders = self.env['sale.order'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['sale', 'done']),  # Solo ordini confermati
            ('id', '!=', self.id or 0)  # Escludere l'ordine attuale se già esiste
        ], order='date_order desc')
        
        if not confirmed_orders:
            _logger.info(f"Nessun ordine precedente trovato per il cliente {self.partner_id.name}")
            return
        
        # Raccogliere gli ultimi 4 prodotti venduti (in ordine cronologico inverso)
        product_ids = []
        seen_products = set()
        
        for order in confirmed_orders:
            # Cercare righe dell'ordine ordinate per ID (ordine di creazione)
            order_lines = order.order_line.filtered(
                lambda line: line.product_id and not line.display_type
            ).sorted('id', reverse=True)  # Più recenti prima
            
            for line in order_lines:
                if line.product_id.id not in seen_products:
                    product_ids.append(line.product_id.id)
                    seen_products.add(line.product_id.id)
                    
                    # Fermarsi quando si raggiungono 4 prodotti unici
                    if len(product_ids) >= 4:
                        break
            
            # Fermarsi se abbiamo già 4 prodotti
            if len(product_ids) >= 4:
                break
        
        if not product_ids:
            _logger.info(f"Nessun prodotto valido trovato negli ultimi ordini del cliente {self.partner_id.name}")
            return
        
        # Creare righe automatiche con quantità 0
        order_lines = []
        for product_id in product_ids:
            product = self.env['product.product'].browse(product_id)
            if product.exists() and product.sale_ok:  # Verificare se il prodotto esiste ancora ed è vendibile
                
                # Cercare unità secondaria se esiste
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
                
                # Aggiungere campi secondari se esistono
                if secondary_uom_id:
                    line_vals.update({
                        'x_secondary_qty': secondary_qty,
                        'x_secondary_uom_id': secondary_uom_id,
                    })
                
                order_lines.append((0, 0, line_vals))
        
        # Applicare le righe all'ordine
        if order_lines:
            self.order_line = order_lines
            _logger.info(f"Create {len(order_lines)} righe automatiche con gli ultimi {len(product_ids)} prodotti per il cliente {self.partner_id.name}")
        else:
            _logger.info(f"Nessuna riga valida creata per il cliente {self.partner_id.name}") 