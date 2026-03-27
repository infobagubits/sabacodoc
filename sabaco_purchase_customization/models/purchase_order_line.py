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
    def onchange_product_id(self):
        """
        Override: esegue la logica standard poi imposta quantità = 0 e purchase_uom_free.
        L'onchange standard chiama _suggest_quantity() che imposta product_qty a 1.0;
        sovrascrivendo qui e impostando 0 dopo super() si garantisce quantità default 0.
        """
        super().onchange_product_id()
        if self.product_id:
            self.product_qty = 0.0
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
            
            # Salva quantità secondaria disponibile del prodotto
            # Usa x_secondary_qty_available del prodotto (stessa logica di qty_available)
            if hasattr(line.product_id.product_tmpl_id, 'x_secondary_qty_available'):
                line.x_secondary_qty_at_confirmation = line.product_id.product_tmpl_id.x_secondary_qty_available
            else:
                line.x_secondary_qty_at_confirmation = 0.0
            
            # Salva UDM secondaria del prodotto
            if hasattr(line.product_id.product_tmpl_id, 'x_secondary_uom_id') and line.product_id.product_tmpl_id.x_secondary_uom_id:
                line.x_secondary_uom_id_at_confirmation = line.product_id.product_tmpl_id.x_secondary_uom_id
            else:
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
                
                # Salva quantità secondaria disponibile del prodotto
                # Usa x_secondary_qty_available del prodotto (stessa logica di qty_available)
                if hasattr(line.product_id.product_tmpl_id, 'x_secondary_qty_available'):
                    line.x_secondary_qty_at_confirmation = line.product_id.product_tmpl_id.x_secondary_qty_available
                else:
                    line.x_secondary_qty_at_confirmation = 0.0
                
                # Salva UDM secondaria del prodotto
                if hasattr(line.product_id.product_tmpl_id, 'x_secondary_uom_id') and line.product_id.product_tmpl_id.x_secondary_uom_id:
                    line.x_secondary_uom_id_at_confirmation = line.product_id.product_tmpl_id.x_secondary_uom_id
                else:
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