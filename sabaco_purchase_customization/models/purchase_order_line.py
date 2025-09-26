from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Campo testo libero per UdM acquisto libera (modificabile)
    purchase_uom_free = fields.Char(
        string='UdM acquisto libera',
        help='Campo libero per inserire un\'unità di misura di acquisto personalizzata.'
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