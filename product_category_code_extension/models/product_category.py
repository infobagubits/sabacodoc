from odoo import models, fields, api

class ProductCategory(models.Model):
    _inherit = 'product.category'

    codice = fields.Char(
        string='Codice',
        help='Codice della categoria'
    )
    
    codice_complessivo = fields.Char(
        string='Codice complessivo',
        help='Codice complessivo della categoria',
        readonly=True
    )
    
    livello = fields.Integer(
        string='Livello',
        help='Livello della categoria nella gerarchia',
        readonly=True,
        compute='_compute_livello',
        store=True
    )

    @api.depends('parent_id')
    def _compute_livello(self):
        """Calcola il livello basato sulla gerarchia dei genitori"""
        for record in self:
            level = 1
            parent = record.parent_id
            while parent:
                level += 1
                parent = parent.parent_id
            record.livello = level

    def write(self, vals):
        """Aggiorna codici quando parent_id cambia"""
        
        for record in self:
            procuct_category = self.env['product.category'].search([('codice', '=', record["codice"]),('parent_id', '=', record["parent_id"])], limit=1)
            if(procuct_category):
                raise ValidationError("Il codice {} è già utilizzato in un'altra categoria con lo stesso genitore.".format(record["codice"]))
        
        
        if 'parent_id' in vals:
            # Verifica se non sta creando loop infinito
            for record in self:
                if vals['parent_id']:
                    parent = self.browse(vals['parent_id'])
                    if record.id in parent._get_all_parent_ids():
                        raise ValidationError("Non è possibile creare una gerarchia circolare!")
        
        result = super().write(vals)
        
        if 'parent_id' in vals or 'codice' in vals:
            # Rigenera codici per record che hanno cambiato genitore o codice
            for record in self:
                record._update_codice_complessivo()
                # Aggiorna figli ricorsivamente
                record._update_children_codes()
        
        return result

    def _update_codice_complessivo(self):
        """Aggiorna il codice complessivo basato sulla gerarchia"""
        for record in self:
            if not record.parent_id:
                # Livello 1: codice complessivo = codice semplice
                record.codice_complessivo = record.codice
            else:
                # Livello > 1: codice complessivo = codice del genitore + codice semplice
                record.codice_complessivo = (record.parent_id.codice_complessivo if record.parent_id.codice_complessivo else '') + (record.codice if record.codice else '')

    def _update_children_codes(self):
        """Aggiorna codici dei figli ricorsivamente"""
        for record in self:
            children = self.search([('parent_id', '=', record.id)])
            for child in children:
                child._update_codice_complessivo()
                child._update_children_codes()

    def _get_all_parent_ids(self):
        """Restituisce tutti gli ID dei genitori nella gerarchia"""
        parent_ids = []
        current = self.parent_id
        while current:
            parent_ids.append(current.id)
            current = current.parent_id
        return parent_ids

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        """Verifica se non ci sono ricorsioni nella gerarchia"""
        for record in self:
            if record.parent_id and record.id in record._get_all_parent_ids():
                raise ValidationError("Non è possibile creare una gerarchia circolare!")