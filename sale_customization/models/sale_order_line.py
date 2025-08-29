# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Unità di misura secondaria (correlata al prodotto)
    x_secondary_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unità Secondaria',
        related='product_id.x_secondary_uom_id',
        store=True,
        readonly=True
    )

    # Quantità nell'unità secondaria (inserita manualmente)
    x_secondary_qty = fields.Float(
        string='Quantità Secondaria',
        help='Quantità nella unità di misura secondaria'
    )

    # Indica se il prodotto ha unità secondaria attiva
    x_secondary_active = fields.Boolean(
        string="Unità Secondaria Attiva",
        related='product_id.product_tmpl_id.x_secondary_uom_id.active',
        store=True,
        readonly=True
    )

    @api.depends('product_id')
    def _compute_available_packaging_ids(self):
        """Override do método padrão com tratamento de erro para produtos sem embalagens"""
        for line in self:
            try:
                # Chama o método original do Odoo
                super(SaleOrderLine, line)._compute_available_packaging_ids()
            except ValueError:
                # Se falhar com ValueError (produto sem embalagens), define lista vazia
                line.available_packaging_ids = [(5, 0, 0)]
                _logger.info(f"Produto {line.product_id.name} sem embalagens - definindo lista vazia")
            except Exception as e:
                # Para outros erros inesperados, log e lista vazia
                _logger.warning(f"Erro inesperado ao computar embalagens para produto {line.product_id.name}: {e}")
                line.available_packaging_ids = [(5, 0, 0)] 