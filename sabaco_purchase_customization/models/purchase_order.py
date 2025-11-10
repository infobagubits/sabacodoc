from odoo import api, fields, models


class PurchaseOrder(models.Model):
    """Inherits the class purchase.order for customizations"""
    _inherit = 'purchase.order'

    purchase_order_for = fields.Selection([
        ('Famù - negozio', 'Famù - negozio'),
        ('Famù - bistrot', 'Famù - bistrot'),
        ('Famù - parco', 'Famù - parco'),
        ('Famù - magazzino centrale', 'Famù - magazzino centrale')
    ])
    
    def write(self, vals):
        """
        Intercetta quando lo stato cambia a 'purchase' e aggiorna i campi di storico nelle linee
        """
        # Salva lo stato precedente per verificare se sta cambiando
        previous_state = {}
        if 'state' in vals and vals['state'] == 'purchase':
            for order in self:
                previous_state[order.id] = order.state
        
        res = super().write(vals)
        
        # Quando l'ordine viene confermato (stato cambia a 'purchase' da un altro stato)
        if 'state' in vals and vals['state'] == 'purchase':
            for order in self:
                # Aggiorna solo se lo stato precedente era diverso da 'purchase'
                if order.id in previous_state and previous_state[order.id] != 'purchase':
                    # Aggiorna i campi di storico in tutte le linee dell'ordine
                    if order.order_line:
                        order.order_line._update_confirmation_fields()
        
        return res