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
            
            # Salva quantità secondaria e UDM secondaria
            if hasattr(line.product_id, 'x_secondary_qty'):
                line.x_secondary_qty_at_confirmation = line.product_id.x_secondary_qty
            if hasattr(line.product_id, 'x_secondary_uom_id'):
                line.x_secondary_uom_id_at_confirmation = line.product_id.x_secondary_uom_id
        
        return line
    
    def write(self, vals):
        """
        Al momento della modifica dello stato, aggiorna i campi se necessario
        """
        res = super().write(vals)
        
        # Se l'ordine viene confermato
        if 'state' in vals and vals['state'] == 'purchase':
            for line in self:
                if line.product_id:
                    # Salva quantità disponibile
                    if not line.qty_available_at_confirmation:
                        line.qty_available_at_confirmation = line.product_id.qty_available
                    
                    # Salva quantità prevista
                    if not line.qty_planned_at_confirmation and hasattr(line.product_id, 'virtual_available'):
                        line.qty_planned_at_confirmation = line.product_id.virtual_available
                    
                    # Salva giorno della settimana
                    if not line.confirmation_weekday:
                        line.confirmation_weekday = line._get_weekday_name(line.order_id.date_approve or line.order_id.date_order)
                    
                    # Salva quantità secondaria e UDM secondaria
                    if hasattr(line.product_id, 'x_secondary_qty'):
                        line.x_secondary_qty_at_confirmation = line.product_id.x_secondary_qty
                    if hasattr(line.product_id, 'x_secondary_uom_id'):
                        line.x_secondary_uom_id_at_confirmation = line.product_id.x_secondary_uom_id
        
        return res