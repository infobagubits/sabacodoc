# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _selection_type(self):
        return [
            ('consu', 'Prodotto'),
            ('service', 'Servizio'),
            ('combo', 'Combo'),
        ]

    # Sovrascrive il campo type per cambiare "Consumabile" in "Prodotto"
    type = fields.Selection(
        selection='_selection_type',
        string="Tipologia prodotto",
        required=True,
        default='consu',
    )
    
    @api.model
    def create(self, vals):
        """
        Crea automaticamente il default_code basato su:
        - codice_complessivo della categoria
        - codice_prodotti_fornitore del fornitore (se presente)
        - sequenziale univoco
        """
        # Esegue la creazione normale
        record = super().create(vals)
        
        # Genera il default_code solo se non è già stato fornito
        if not record.default_code:
            record.default_code = record._generate_default_code()
        
        return record
    
    def _generate_default_code(self):
        """
        Genera il codice prodotto basato su categoria e fornitore
        
        Formato: CATEGORIA_FORNITORE-SEQUENZIALE
        Esempio: FM01ABC123-001
        """
        codes = []
        
        # 1. Codice categoria (codice_complessivo)
        if self.categ_id and self.categ_id.codice_complessivo:
            codes.append(self.categ_id.codice_complessivo)
        
        # 2. Codice fornitore (codice_prodotti_fornitore)
        if self.seller_ids and self.seller_ids[0]:
            partner = self.seller_ids[0].partner_id  # campo correto
            if partner and hasattr(partner, 'codice_prodotti_fornitore') and partner.codice_prodotti_fornitore:
                codes.append(partner.codice_prodotti_fornitore)
        
        # Se non ci sono codici, non generare nulla
        if not codes:
            return ''
        
        # Concatena i codici (senza separatori)
        base_code = ''.join(codes)
        
        # Trova il prossimo sequenziale disponibile
        # Cerca tutti i prodotti con lo stesso base_code
        existing = self.env['product.template'].search([
            ('default_code', 'like', base_code + '%')
        ])
        
        # Estrae i numeri esistenti dalla fine del default_code
        max_seq = 0
        for product in existing:
            if product.default_code and product.default_code.startswith(base_code):
                # Rimuove il base_code per ottenere solo il numero finale
                seq_str = product.default_code[len(base_code):]
                if seq_str and seq_str.isdigit():
                    try:
                        seq_num = int(seq_str)
                        if seq_num > max_seq:
                            max_seq = seq_num
                    except ValueError:
                        pass
        
        # Genera il nuovo sequenziale
        new_seq = max_seq + 1
        
        # Ritorna il codice completo con sequenziale senza zeri iniziali
        return f"{base_code}{new_seq}"

