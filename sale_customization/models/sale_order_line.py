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

    @api.depends('product_id', 'order_id.partner_id')
    def _compute_available_packaging_ids(self):
        """
        Override do método padrão com tratamento de erro para produtos sem embalagens
        e lógica personalizada para filtragem por cliente e flag de vendas
        """
        for line in self:
            try:
                if not line.product_id:
                    line.available_packaging_ids = [(5, 0, 0)]  # Rimuove tutti
                    continue
                
                # Cerca tutti gli imballaggi del prodotto che sono per VENDITE
                all_sales_packagings = self.env['product.packaging'].search([
                    ('product_id', '=', line.product_id.id),
                    ('sales', '=', True)  # SOLO embalagens de vendas
                ])
                
                # Se c'è un cliente selezionato
                if line.order_id.partner_id:
                    # Cerca imballaggi collegati a questo cliente (che siano per vendite)
                    # IMPORTANTE: Considera apenas parceiros que são CLIENTES
                    partner_packagings = all_sales_packagings.filtered(
                        lambda p: line.order_id.partner_id.id in p.contact_line_ids.filtered(
                            lambda c: c.partner_id.is_customer
                        ).partner_id.ids
                    )
                    
                    if partner_packagings:
                        # PRIORITÀ: Se esistono imballaggi collegati al cliente, mostra solo quelli
                        line.available_packaging_ids = [(6, 0, partner_packagings.ids)]
                    else:
                        # FALLBACK: Se non ci sono imballaggi collegati al cliente, mostra solo quelli SENZA CLIENTE
                        no_customer_packagings = all_sales_packagings.filtered(
                            lambda p: not p.contact_line_ids.filtered(lambda c: c.partner_id.is_customer)
                        )
                        line.available_packaging_ids = [(6, 0, no_customer_packagings.ids)]
                else:
                    # Se non c'è un cliente, mostra solo gli imballaggi senza cliente
                    no_customer_packagings = all_sales_packagings.filtered(
                        lambda p: not p.contact_line_ids.filtered(lambda c: c.partner_id.is_customer)
                    )
                    line.available_packaging_ids = [(6, 0, no_customer_packagings.ids)]
                    
            except ValueError:
                # Se falhar com ValueError (produto sem embalagens), define lista vazia
                line.available_packaging_ids = [(5, 0, 0)]
                _logger.info(f"Produto {line.product_id.name} sem embalagens - definindo lista vazia")
            except Exception as e:
                # Para outros erros inesperados, log e lista vazia
                _logger.warning(f"Erro inesperado ao computar embalagens para produto {line.product_id.name}: {e}")
                line.available_packaging_ids = [(5, 0, 0)] 