from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campo para selecionar a unidade de medida secundária
    x_secondary_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unità di Misura Secondaria',
        help='Unità secondaria utilizzata per la visualizzazione aggiuntiva.'
    )

    # Campo computado que calcula a quantidade secundária disponível baseado em stock.quant
    x_secondary_qty_available = fields.Float(
        string='Quantità Secondaria Disponibile',
        compute='_compute_secondary_qty_available',  # Agora é calculado automaticamente
        store=False,  # Não armazenado - sempre calculado em tempo real
        help='Quantità secondaria disponibile calcolata automaticamente dai movimenti di magazzino.'
    )
    
    # Campo que exibe a quantidade secundária formatada com unidade (ex: 24.00 PZ)
    x_secondary_qty_display = fields.Char(
        string='Quantità Secondaria Formattata',
        compute='_compute_secondary_qty_display',
        store=False
    )

    def _compute_secondary_qty_available(self):
        """
        Calcula a quantidade secundária disponível somando os stock.quant
        de todas as localizações internas do produto.
        Similar ao cálculo de qty_available do Odoo.
        """
        for template in self:
            total_secondary = 0.0
            
            # Se não tem unidade secundária, quantidade é zero
            if not template.x_secondary_uom_id:
                template.x_secondary_qty_available = 0.0
                continue
            
            # Busca todos os quants do produto em localizações internas
            quants = self.env['stock.quant'].search([
                ('product_tmpl_id', '=', template.id),
                ('location_id.usage', '=', 'internal'),  # Apenas localizações internas
            ])
            
            # Soma as quantidades secundárias de cada quant
            for quant in quants:
                total_secondary += quant.x_secondary_qty
            
            template.x_secondary_qty_available = total_secondary

    # Função dummy que é obrigatória para ativar o botão de estatística
    def action_dummy_secondary_qty(self):
        """Função dummy para ativar o botão de estatística"""
        return

    # Função que monta o texto exibido no botão (ex: "24.00 PZ")
    @api.depends('x_secondary_qty_available', 'x_secondary_uom_id.name')
    def _compute_secondary_qty_display(self):
        for template in self:
            uom_name = template.x_secondary_uom_id.name or ''
            qty = template.x_secondary_qty_available or 0.0
            if uom_name:
                template.x_secondary_qty_display = f"{qty:.2f} {uom_name}"
            else:
                template.x_secondary_qty_display = f"{qty:.2f}"
