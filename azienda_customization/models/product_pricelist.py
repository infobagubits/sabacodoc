# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def unlink(self):
        if any(record.id == 1 for record in self):
            raise UserError(_("Non è possibile eliminare il listino prezzi principale (ID 1)."))
        return super().unlink()
