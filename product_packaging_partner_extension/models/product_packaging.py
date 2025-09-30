from odoo import models, fields, api

class ProductPackaging(models.Model):
    _inherit = 'product.packaging'

    contact_line_ids = fields.One2many(
        'product.packaging.partner.rel',
        'packaging_id',
        string='Contatti'
    )
    
    # Campo Many2many computado para mostrar parceiros na lista
    linked_partner_ids = fields.Many2many(
        'res.partner',
        compute='_compute_linked_partner_ids',
        string='Parceiros Vinculados',
        store=False
    )

    @api.depends('contact_line_ids.partner_id')
    def _compute_linked_partner_ids(self):
        """Computa os parceiros vinculados a partir das linhas de contato"""
        for packaging in self:
            packaging.linked_partner_ids = packaging.contact_line_ids.mapped('partner_id')

    @api.model
    def search_packaging_for_partner(self, product_id, partner_id):
        """
        Restituisce imballaggi filtrati per partner:
        - Se partner_id e ci sono imballaggi collegati: solo imballaggi del partner
        - Altrimenti: tutti gli imballaggi del prodotto
        """
        domain = [('product_id', '=', product_id)]
        
        if partner_id:
            # Verifica se esistono imballaggi collegati a questo partner
            partner_packagings = self.search([
                ('product_id', '=', product_id),
                ('contact_line_ids.partner_id', '=', partner_id)
            ])
            
            if partner_packagings:
                # Se esistono imballaggi collegati, mostra solo quelli
                domain.append(('contact_line_ids.partner_id', '=', partner_id))
        
        return self.search(domain)

class ProductPackagingPartnerRel(models.Model):
    _name = 'product.packaging.partner.rel'
    _description = 'Contatto collegato all\'imballaggio'

    packaging_id = fields.Many2one('product.packaging', string='Imballaggio', required=True, ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner',
        string='Nome',
        required=True,
        domain="['|', ('is_customer', '=', True), ('is_supplier', '=', True)]"
    )
    partner_type = fields.Char(
        string='Tipo',
        compute='_compute_partner_type',
        store=False
    )

    _sql_constraints = [
        (
            'unique_packaging_partner',
            'unique(packaging_id, partner_id)',
            'Lo stesso contatto non può essere collegato più di una volta allo stesso imballaggio!'
        ),
    ]

    @api.depends('partner_id')
    def _compute_partner_type(self):
        for rec in self:
            tipi = []
            if rec.partner_id.is_customer:
                tipi.append('Cliente')
            if rec.partner_id.is_supplier:
                tipi.append('Fornitore')
            rec.partner_type = ', '.join(tipi) 