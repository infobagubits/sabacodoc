from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    codice = fields.Char(
        string='Codice',
        help='Codice della categoria',
        readonly=True
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

    @api.model_create_multi
    def create(self, vals_list):
        """Genera codici automaticamente alla creazione"""
        for vals in vals_list:
            if not vals.get('codice'):
                vals['codice'] = self._generate_next_code(vals.get('parent_id'), vals.get('name', ''))
        
        records = super().create(vals_list)
        
        for record in records:
            record._update_codice_complessivo()
        
        return records

    def write(self, vals):
        """Aggiorna codici quando parent_id cambia"""
        if 'parent_id' in vals:
            # Verifica se non sta creando loop infinito
            for record in self:
                if vals['parent_id']:
                    parent = self.browse(vals['parent_id'])
                    if record.id in parent._get_all_parent_ids():
                        raise ValidationError("Non è possibile creare una gerarchia circolare!")
        
        result = super().write(vals)
        
        if 'parent_id' in vals or 'name' in vals:
            # Rigenera codici per record che hanno cambiato genitore o nome
            for record in self:
                if not record.parent_id:  # Solo per livello 1 se è cambiato il nome
                    if 'name' in vals:
                        record.codice = record._generate_code_from_name(record.name)
                elif not record.codice or 'parent_id' in vals:
                    record.codice = record._generate_next_code(record.parent_id.id if record.parent_id else False, record.name)
                record._update_codice_complessivo()
                # Aggiorna figli ricorsivamente
                record._update_children_codes()
        
        return result

    def _generate_code_from_name(self, name):
        """Genera codice basato sul nome della categoria seguendo le regole specifiche"""
        if not name:
            return 'XX'
        
        # Rimuove caratteri speciali e converte in maiuscolo
        clean_name = name.upper().strip()
        _logger.info(f"Generazione codice per: '{name}' -> '{clean_name}'")
        
        # Lista di preposizioni e articoli in italiano da ignorare
        ignore_words = {
            'DI', 'DEL', 'DELLA', 'DELLE', 'DEI', 'DEGLI', 'IL', 'LA', 'LE', 'LO', 'GLI', 'UN', 'UNA',
            'IN', 'CON', 'PER', 'SU', 'TRA', 'FRA', 'DA', 'A', 'E', 'DE'  # Aggiunto 'DE' per portoghese
        }
        
        # Regola SPECIALE: Se ha barra (/), combina prima lettera prima + prima lettera dopo
        if '/' in clean_name:
            _logger.info(f"Trovata barra in: '{clean_name}'")
            
            # Divide per barra
            parts = clean_name.split('/')
            if len(parts) >= 2:
                before_slash = parts[0].strip()  # Prima della barra
                after_slash = parts[-1].strip()  # Dopo la barra
                
                _logger.info(f"Prima della barra: '{before_slash}'")
                _logger.info(f"Dopo la barra: '{after_slash}'")
                
                # Estrae parole prima della barra
                words_before = re.findall(r'\b\w+', before_slash)
                meaningful_before = [word for word in words_before if word not in ignore_words and len(word) > 1]
                
                # Estrae parole dopo la barra
                words_after = re.findall(r'\b\w+', after_slash)
                meaningful_after = [word for word in words_after if word not in ignore_words and len(word) > 1]
                
                _logger.info(f"Parole significative prima: {meaningful_before}")
                _logger.info(f"Parole significative dopo: {meaningful_after}")
                
                # Prende prima lettera della prima parola significativa prima della barra
                letter_before = ''
                if meaningful_before:
                    letter_before = meaningful_before[0][0]
                elif words_before:
                    letter_before = words_before[0][0]
                
                # Prende prima lettera della prima parola significativa dopo la barra
                letter_after = ''
                if meaningful_after:
                    letter_after = meaningful_after[0][0]
                elif words_after:
                    letter_after = words_after[0][0]
                
                _logger.info(f"Lettera prima: '{letter_before}', Lettera dopo: '{letter_after}'")
                
                # Combina le due lettere
                if letter_before and letter_after:
                    code = letter_before + letter_after
                    _logger.info(f"Codice generato (barra): {code}")
                    return code
                elif letter_after:
                    # Se non ha parola prima, usa solo dopo (prime due lettere)
                    code = meaningful_after[0][:2] if meaningful_after else words_after[0][:2]
                    _logger.info(f"Codice generato (solo dopo barra): {code}")
                    return code
                elif letter_before:
                    # Se non ha parola dopo, usa solo prima (prime due lettere)
                    code = meaningful_before[0][:2] if meaningful_before else words_before[0][:2]
                    _logger.info(f"Codice generato (solo prima barra): {code}")
                    return code
        
        # Regola 2: Se NON ha barra - parole multiple, prima lettera di ogni (ignorando preposizioni)
        words = re.findall(r'\b\w+', clean_name)
        _logger.info(f"Elaborazione senza barra - Parole: {words}")
        
        # Filtra parole ignorabili
        meaningful_words = [word for word in words if word not in ignore_words and len(word) > 1]
        _logger.info(f"Parole significative: {meaningful_words}")
        
        if len(meaningful_words) >= 2:
            # Prima lettera di ogni parola significativa (massimo 2)
            code = ''.join([word[0] for word in meaningful_words[:2]])
            _logger.info(f"Codice generato (parole multiple): {code}")
            return code
        elif len(meaningful_words) == 1:
            # Regola 3: Parola singola significativa, prime due lettere
            word = meaningful_words[0]
            code = word[:2] if len(word) >= 2 else word + 'X'
            _logger.info(f"Codice generato (parola singola): {code}")
            return code
        elif len(words) >= 2:
            # Fallback: se non ha parole significative, usa le prime due parole
            code = ''.join([word[0] for word in words[:2]])
            _logger.info(f"Codice generato (fallback multiple): {code}")
            return code
        elif len(words) == 1:
            # Fallback: parola singola
            word = words[0]
            code = word[:2] if len(word) >= 2 else word + 'X'
            _logger.info(f"Codice generato (fallback singola): {code}")
            return code
        
        # Fallback finale
        _logger.info("Usando fallback finale: XX")
        return 'XX'

    def _generate_next_code(self, parent_id, name=''):
        """Genera il prossimo codice sequenziale per il genitore specificato"""
        if not parent_id:
            # Livello 1: codici basati sul nome
            if name:
                base_code = self._generate_code_from_name(name)
                
                # Verifica se il codice esiste già
                existing_codes = self.search([('parent_id', '=', False)]).mapped('codice')
                existing_codes = [code for code in existing_codes if code]
                
                if base_code not in existing_codes:
                    return base_code
                
                # Se esiste già, aggiunge numero sequenziale
                counter = 1
                while f"{base_code}{counter:02d}" in existing_codes:
                    counter += 1
                return f"{base_code}{counter:02d}"
            
            # Fallback per codici standard se non ha nome
            existing_codes = self.search([('parent_id', '=', False)]).mapped('codice')
            existing_codes = [code for code in existing_codes if code]
            
            level1_codes = ['AC', 'CD', 'CL', 'FM', 'IM', 'MP', 'PF', 'SC', 'SV', 'UT']
            
            for code in level1_codes:
                if code not in existing_codes:
                    return code
            
            # Se tutti i codici standard sono stati usati, genera nuovi
            import string
            for i, letter1 in enumerate(string.ascii_uppercase):
                for letter2 in string.ascii_uppercase:
                    code = letter1 + letter2
                    if code not in existing_codes and code not in level1_codes:
                        return code
        else:
            # Livelli 2 e 3: codici numerici sequenziali (01, 02, 03...)
            siblings = self.search([('parent_id', '=', parent_id)])
            existing_numbers = []
            
            for sibling in siblings:
                if sibling.codice and sibling.codice.isdigit():
                    existing_numbers.append(int(sibling.codice))
            
            next_number = 1
            while next_number in existing_numbers:
                next_number += 1
            
            return f"{next_number:02d}"  # Formato 01, 02, 03...

    def _update_codice_complessivo(self):
        """Aggiorna il codice complessivo basato sulla gerarchia"""
        for record in self:
            if not record.parent_id:
                # Livello 1: codice complessivo = codice semplice
                record.codice_complessivo = record.codice
            else:
                # Livelli 2+: concatena codici dei genitori
                parent_codes = []
                current = record
                
                while current.parent_id:
                    current = current.parent_id
                    if current.codice:
                        parent_codes.insert(0, current.codice)
                
                if parent_codes and record.codice:
                    if record.livello == 2:
                        # Livello 2: PARENT + CODE (es: FM01)
                        record.codice_complessivo = parent_codes[0] + record.codice
                    else:
                        # Livello 3+: PARENT.CODE (es: FM01.01)
                        parent_full = parent_codes[0] + record.parent_id.codice
                        record.codice_complessivo = parent_full + '.' + record.codice

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

    @api.model
    def _populate_existing_codes(self):
        """Popola codici per categorie esistenti senza codice"""
        # Elabora prima i livelli più alti (genitori) poi i figli
        categories_without_code = self.search([('codice', '=', False)], order='parent_id asc, id asc')
        
        for category in categories_without_code:
            # Genera codice se non esiste
            if not category.codice:
                category.codice = category._generate_next_code(
                    category.parent_id.id if category.parent_id else False, 
                    category.name
                )
            
            # Aggiorna codice complessivo
            category._update_codice_complessivo()
        
        return True

    @api.model
    def test_code_generation(self, test_name):
        """Metodo di test per debug generazione codici"""
        code = self._generate_code_from_name(test_name)
        _logger.info(f"TEST: '{test_name}' -> '{code}'")
        return code 