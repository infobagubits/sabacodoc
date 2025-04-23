from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campo para selecionar a unidade de medida secundária (Many2one com 'uom.uom')
    x_secondary_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unità di Misura Secondaria',  # Texto que será exibido na interface
        help='Unità secondaria utilizzata per la visualizzazione aggiuntiva.'  # Texto de ajuda
    )

    # Campo que armazena a quantidade convertida na unidade secundária
    x_secondary_qty_available = fields.Float(
        string='Quantità Secondaria Disponibile',  # Rótulo do campo
        #compute='_compute_secondary_qty_available',  # Campo calculado automaticamente
        help='Quantità disponibile convertita nell’unità di misura secondaria.'  # Ajuda na interface
    )
    
    # Campo que exibe a quantidade secundária formatada com unidade (ex: 24.00 PZ)
    x_secondary_qty_display = fields.Char(
        string='Quantità Secondaria Formattata',  # Texto mostrado no botão de topo
        compute='_compute_secondary_qty_display',  # Calculado dinamicamente
        store=False  # Não é salvo no banco, apenas exibido dinamicamente
    )


    # Função dummy que é obrigatória para ativar o botão de estatística (não faz nada)
    def action_dummy_secondary_qty(self):
        """Função dummy para ativar o botão de estatística"""
        return

    # Função que monta o texto exibido no botão (ex: "24.00 PZ")
    @api.depends('x_secondary_qty_available', 'x_secondary_uom_id.name')
    def _compute_secondary_qty_display(self):
        for template in self:
            uom_name = template.x_secondary_uom_id.name or ''  # Nome da unidade (ex: PZ)
            qty = template.x_secondary_qty_available or 0.0
            # Se tiver unidade, mostra com o nome dela; senão só o número
            if uom_name:
                template.x_secondary_qty_display = f"{qty:.2f} {uom_name}"
            else:
                template.x_secondary_qty_display = f"{qty:.2f}"
