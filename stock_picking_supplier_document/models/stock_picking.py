from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    supplier_document_number = fields.Char(
        string="Num. documento fornitore",
        help="Numero del documento del fornitore"
    )
    
    supplier_document_date = fields.Date(
        string="Data documento fornitore",
        help="Data del documento del fornitore"
    )

    @api.onchange('supplier_document_number', 'partner_id')
    def _onchange_check_duplicate_supplier_document(self):
        """
        Mostra un avviso se esiste già un altro movimento in ingresso
        con lo stesso fornitore e numero documento fornitore.
        """
        if not self.supplier_document_number or not self.partner_id:
            return
        
        # Verifica solo per operazioni di ricezione (incoming)
        if self.picking_type_id.code != 'incoming':
            return
        
        # Cerca duplicati
        domain = [
            ('id', '!=', self._origin.id if self._origin else False),
            ('partner_id', '=', self.partner_id.id),
            ('supplier_document_number', '=', self.supplier_document_number),
            ('picking_type_id.code', '=', 'incoming'),
            ('state', '!=', 'cancel'),
        ]
        
        duplicates = self.env['stock.picking'].search(domain, limit=5)
        
        if duplicates:
            duplicate_names = ', '.join(duplicates.mapped('name'))
            return {
                'warning': {
                    'title': _('Documento fornitore duplicato'),
                    'message': _(
                        'Attenzione! Esiste già un movimento in ingresso con lo stesso '
                        'fornitore "%s" e numero documento "%s".\n\n'
                        'Documenti trovati: %s\n\n'
                        'Verificare se non si tratta di un duplicato.'
                    ) % (self.partner_id.name, self.supplier_document_number, duplicate_names),
                    'type': 'notification',
                }
            } 