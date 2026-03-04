from odoo import models, fields, api, _
from odoo.exceptions import UserError


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
    
    # Campo computado per mostrare il banner di avviso duplicato
    duplicate_supplier_document_warning = fields.Char(
        string="Avviso documento duplicato",
        compute='_compute_duplicate_supplier_document_warning',
        store=False,
    )

    @api.depends('supplier_document_number', 'partner_id', 'picking_type_id')
    def _compute_duplicate_supplier_document_warning(self):
        """
        Calcola se esiste un documento duplicato e restituisce il messaggio di avviso.
        """
        for picking in self:
            picking.duplicate_supplier_document_warning = False
            
            if not picking.supplier_document_number or not picking.partner_id:
                continue
            
            # Verifica solo per operazioni di ricezione (incoming)
            if not picking.picking_type_id or picking.picking_type_id.code != 'incoming':
                continue
            
            # Cerca duplicati
            domain = [
                ('id', '!=', picking.id),
                ('partner_id', '=', picking.partner_id.id),
                ('supplier_document_number', '=', picking.supplier_document_number),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', '!=', 'cancel'),
            ]
            
            duplicates = self.env['stock.picking'].search(domain, limit=5)
            
            if duplicates:
                duplicate_names = ', '.join(duplicates.mapped('name'))
                picking.duplicate_supplier_document_warning = _(
                    'Attenzione! Esiste già un movimento in ingresso con lo stesso '
                    'fornitore "%(partner)s" e numero documento "%(doc_num)s". '
                    'Documenti trovati: %(duplicates)s'
                ) % {
                    'partner': picking.partner_id.name,
                    'doc_num': picking.supplier_document_number,
                    'duplicates': duplicate_names,
                } 

    def button_validate(self):
        """Blocca la convalida se la ricezione (incoming) non ha numero e data documento fornitore."""
        incoming = self.filtered(
            lambda p: p.picking_type_id.code == 'incoming' and p.state not in ('done', 'cancel')
        )
        for picking in incoming:
            if not picking.supplier_document_number or not picking.supplier_document_date:
                raise UserError(_(
                    'Per convalidare la ricezione "%(name)s" è obbligatorio compilare '
                    'il numero e la data del documento fornitore.'
                ) % {'name': picking.name})
        return super().button_validate()