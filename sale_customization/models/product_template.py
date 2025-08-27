from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campo per selezionare l'unità di misura secondaria (Many2one con 'uom.uom')
    x_secondary_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unità di Misura Secondaria',  # Texto che sarà visualizzato nell'interfaccia
        help='Unità secondaria utilizzata per la visualizzazione aggiuntiva.'  # Texto di aiuto
    )

    # Campo che memorizza la quantità convertita nell'unità secondaria
    x_secondary_qty_available = fields.Float(
        string='Quantità Secondaria Disponibile',  # Etichetta del campo
        help='Quantità disponibile convertita nell\'unità di misura secondaria.'  # Aiuto nell'interfaccia
    )
    
    # Campo che visualizza la quantità secondaria formattata con unità (es: 24.00 PZ)
    x_secondary_qty_display = fields.Char(
        string='Quantità Secondaria Formattata',  # Testo mostrato nel pulsante in alto
        compute='_compute_secondary_qty_display',  # Calcolato dinamicamente
        store=False  # Non è salvato nel database, solo visualizzato dinamicamente
    )


    # Funzione dummy che è obbligatoria per attivare il pulsante di statistica (non fa nulla)
    def action_dummy_secondary_qty(self):
        """Funzione dummy per attivare il pulsante di statistica"""
        return

    # Funzione che costruisce il testo visualizzato nel pulsante (es: "24.00 PZ")
    @api.depends('x_secondary_qty_available', 'x_secondary_uom_id.name')
    def _compute_secondary_qty_display(self):
        for template in self:
            uom_name = template.x_secondary_uom_id.name or ''  # Nome dell'unità (es: PZ)
            qty = template.x_secondary_qty_available or 0.0
            # Se ha unità, mostra con il nome di essa; altrimenti solo il numero
            if uom_name:
                template.x_secondary_qty_display = f"{qty:.2f} {uom_name}"
            else:
                template.x_secondary_qty_display = f"{qty:.2f}"
