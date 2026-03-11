from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Aspetto esteriore dei beni (sezione DDT - spedizioni)
    aspetto_esteriore_beni = fields.Selection(
        [
            ('pallet', 'Pallet'),
            ('a_vista', 'A vista'),
            ('scatole', 'Scatole'),
        ],
        string='Aspetto esteriore dei beni',
        help='Aspetto esteriore dei beni nella spedizione (sezione Informazioni DDT).',
    )

    # Campi correlati al giro di ordini
    giro_id = fields.Many2one(
        'giri.ordine', 
        string="Giro di Consegna",
        related='sale_id.giro_id',
        readonly=True,
        help="Giro di consegna associato a questo picking"
    )
    
    sequenza_consegna = fields.Integer(
        string="Sequenza di Consegna",
        related='sale_id.sequenza_consegna', 
        readonly=True,
        help="Sequenza di consegna nel giro"
    )
