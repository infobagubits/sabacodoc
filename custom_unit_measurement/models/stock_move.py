from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'
    
    # Unità Secondaria: prelevata dal prodotto; sola lettura, memorizzata per la view
    x_secondary_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Unità Secondaria',
        related='product_id.x_secondary_uom_id',
        store=True,
        readonly=True
    )
    
    # Quantità Secondaria: inserita manualmente
    x_secondary_qty = fields.Float(
        string='Quantità Secondaria',
        help='Inserisci manualmente la quantità secondaria nel movimento.'
    )
    
    # Indica se l'unità secondaria è attiva (legato al campo active di uom.uom)
    x_secondary_active = fields.Boolean(
        string="Unità Secondaria Attiva",
        related='product_id.x_secondary_uom_id.active',
        store=True,
        readonly=True
    )
    
    # Quantità Secondaria Virtuale (calcolata dinamicamente)
    x_secondary_qty_virtual = fields.Float(
        string='Quantità Secondaria Virtuale',
        compute='_compute_virtual_secondary_qty',
        store=False
    )
    
    # Indica se la quantità secondaria supera lo stock disponibile
    x_secondary_qty_exceeds_stock = fields.Boolean(
        string="Supera lo stock secondario",
        compute='_compute_exceeds_secondary_qty',
        store=True
    )
    
    # Campo relacionado para exibir ou não as colunas de unidade e quantidade secundária
    display_secondary = fields.Boolean(
        string="Exibir Colunas Secundarie",
        related='picking_id.has_secondary',
        store=True,
        readonly=True
    )

    @api.depends('x_secondary_qty', 'product_id.x_secondary_qty_available')
    def _compute_exceeds_secondary_qty(self):
        # Calcula se a quantidade secundária excede o estoque disponível para movimentos de saída
        for move in self:
            move.x_secondary_qty_exceeds_stock = (
                move.picking_id.picking_type_code == 'outgoing' and
                move.x_secondary_qty and
                move.product_id.x_secondary_qty_available is not None and
                move.x_secondary_qty > move.product_id.x_secondary_qty_available
            )
    
    def _compute_virtual_secondary_qty(self):
        # Neste exemplo, a quantidade virtual é igual à quantidade inserida
        for rec in self:
            rec.x_secondary_qty_virtual = rec.x_secondary_qty

    @api.model
    def create(self, vals):
        """
        Após o Odoo agrupar a move, somamos também o x_secondary_qty manualmente.
        """
        picking_id = vals.get('picking_id')
        product_id = vals.get('product_id')
        secondary_to_add = vals.get('x_secondary_qty', 0.0)

        move = super().create(vals)

        if picking_id and product_id and secondary_to_add:
            domain = [
                ('picking_id', '=', picking_id),
                ('product_id', '=', product_id),
                ('location_id', '=', move.location_id.id),
                ('location_dest_id', '=', move.location_dest_id.id),
                ('state', 'in', ['draft', 'confirmed', 'assigned']),
            ]
            grouped_move = self.env['stock.move'].search(domain, limit=1)

            # Garantir que não é a própria move recém-criada
            if grouped_move and grouped_move.id != move.id:
                grouped_move.x_secondary_qty += secondary_to_add

        return move