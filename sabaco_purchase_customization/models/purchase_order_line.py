from odoo import models, fields, api
from datetime import datetime

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Campo testo libero per UdM acquisto libera (modificabile)
    purchase_uom_free = fields.Char(
        string='UdM acquisto libera',
        help='Campo libero per inserire un\'unità di misura di acquisto personalizzata.'
    )
    
    # Campi per storico acquisti
    qty_available_at_confirmation = fields.Float(
        string='Qt. a disposizione',
        help='Quantità disponibile al momento della conferma dell\'ordine',
        readonly=True,
    )
    
    qty_planned_at_confirmation = fields.Float(
        string='Qt. prevista',
        help='Quantità prevista al momento della conferma dell\'ordine',
        readonly=True,
    )
    
    confirmation_weekday = fields.Char(
        string='Giorno settimana',
        help='Giorno della settimana in cui è stato confermato l\'ordine',
        readonly=True,
        store=True,
    )
    
    x_secondary_qty_at_confirmation = fields.Float(
        string='Qty. secondaria',
        help='Quantità secondaria al momento della conferma dell\'ordine',
        readonly=True,
    )
    
    x_secondary_uom_id_at_confirmation = fields.Many2one(
        'uom.uom',
        string='UdM secondaria',
        help='Unità di misura secondaria al momento della conferma dell\'ordine',
        readonly=True,
        store=True,
    )

    @api.onchange('product_id')
    def _onchange_product_id_purchase_uom_free(self):
        """
        Preenche automaticamente o campo purchase_uom_free com o valor do campo
        x_studio_unita_di_acquisto_libera do produto quando um produto é selecionado
        """
        if self.product_id and hasattr(self.product_id, 'x_studio_unita_di_acquisto_libera'):
            self.purchase_uom_free = self.product_id.x_studio_unita_di_acquisto_libera
        else:
            self.purchase_uom_free = False
    
    def _get_weekday_name(self, date):
        """
        Restituisce il nome del giorno della settimana in italiano
        """
        if not date:
            return False
        
        weekdays = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        if isinstance(date, str):
            date = fields.Datetime.from_string(date)
        return weekdays[date.weekday()]
    
    @api.model
    def create(self, vals):
        """
        Al momento della creazione, salva quantità disponibile e prevista
        Solo quando l'ordine è confermato (state=purchase)
        """
        line = super().create(vals)
        
        if line.order_id.state == 'purchase' and line.product_id:
            # Salva quantità disponibile
            line.qty_available_at_confirmation = line.product_id.qty_available
            
            # Salva quantità prevista (futura)
            if hasattr(line.product_id, 'virtual_available'):
                line.qty_planned_at_confirmation = line.product_id.virtual_available
            
            # Salva giorno della settimana
            line.confirmation_weekday = line._get_weekday_name(line.order_id.date_approve or line.order_id.date_order)
            
            # Calcola e salva quantità secondaria
            # Usa la quantità principale del pedido (product_uom_qty) e converte per la UDM secondaria
            if hasattr(line.product_id.product_tmpl_id, 'x_secondary_uom_id') and line.product_id.product_tmpl_id.x_secondary_uom_id:
                secondary_uom = line.product_id.product_tmpl_id.x_secondary_uom_id
                primary_uom = line.product_uom or line.product_id.uom_id
                primary_qty = line.product_uom_qty or 0.0
                
                # Calcola la quantità secondaria usando la conversione tra unità
                line.x_secondary_qty_at_confirmation = line._calculate_secondary_qty(
                    primary_qty, 
                    primary_uom, 
                    secondary_uom
                )
                line.x_secondary_uom_id_at_confirmation = secondary_uom
            else:
                # Se non c'è unità secondaria, azzera i campi
                line.x_secondary_qty_at_confirmation = 0.0
                line.x_secondary_uom_id_at_confirmation = False
        
        return line
    
    def _calculate_secondary_qty(self, primary_qty, primary_uom, secondary_uom):
        """
        Calcola la quantità secondaria a partire dalla quantità principale.
        Usa la conversione standard del Odoo tra unità di misura.
        """
        if not primary_qty or not primary_uom or not secondary_uom:
            return 0.0
        
        # Verifica se le unità appartengono alla stessa categoria
        if primary_uom.category_id != secondary_uom.category_id:
            return 0.0
        
        # Usa il metodo standard del Odoo per convertire tra unità
        try:
            secondary_qty = primary_uom._compute_quantity(
                primary_qty, 
                secondary_uom, 
                round=True
            )
            return secondary_qty
        except Exception:
            # Se la conversione fallisce, ritorna 0
            return 0.0
    
    def _update_confirmation_fields(self):
        """
        Aggiorna i campi di storico quando l'ordine viene confermato.
        Questo metodo viene chiamato quando purchase.order cambia stato a 'purchase'.
        Aggiorna sempre i campi quando l'ordine viene confermato per la prima volta.
        """
        for line in self:
            if line.product_id and line.order_id.state == 'purchase':
                # Salva quantità disponibile
                line.qty_available_at_confirmation = line.product_id.qty_available
                
                # Salva quantità prevista (virtual_available)
                if hasattr(line.product_id, 'virtual_available'):
                    line.qty_planned_at_confirmation = line.product_id.virtual_available
                
                # Salva giorno della settimana
                if not line.confirmation_weekday:
                    line.confirmation_weekday = line._get_weekday_name(line.order_id.date_approve or line.order_id.date_order)
                
                # Calcola e salva quantità secondaria
                # Usa la quantità principale del pedido (product_uom_qty) e converte per la UDM secondaria
                if hasattr(line.product_id.product_tmpl_id, 'x_secondary_uom_id') and line.product_id.product_tmpl_id.x_secondary_uom_id:
                    secondary_uom = line.product_id.product_tmpl_id.x_secondary_uom_id
                    primary_uom = line.product_uom or line.product_id.uom_id
                    primary_qty = line.product_uom_qty or 0.0
                    
                    # Calcola la quantità secondaria usando la conversione tra unità
                    line.x_secondary_qty_at_confirmation = self._calculate_secondary_qty(
                        primary_qty, 
                        primary_uom, 
                        secondary_uom
                    )
                    line.x_secondary_uom_id_at_confirmation = secondary_uom
                else:
                    # Se non c'è unità secondaria, azzera i campi
                    line.x_secondary_qty_at_confirmation = 0.0
                    line.x_secondary_uom_id_at_confirmation = False
    
    def write(self, vals):
        """
        Al momento della modifica dello stato, aggiorna i campi se necessario
        """
        res = super().write(vals)
        
        # Se l'ordine viene confermato (quando state viene scritto direttamente nella linea)
        if 'state' in vals and vals['state'] == 'purchase':
            self._update_confirmation_fields()
        
        return res