from odoo import models, fields, api


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