from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean(string="Cliente")
    is_supplier = fields.Boolean(
        string="Fornitore",
        help="Se questo partner è un fornitore, verrà mostrata la scheda Prodotti"
    )

    # Campi per la scheda Prodotti
    supplier_product_ids = fields.One2many(
        'product.supplierinfo',
        'partner_id',
        string='Prodotti del Fornitore',
        help='Prodotti dove questo partner è fornitore'
    )

    # Campi deprecati - mantenuti per compatibilità ma nascosti nelle view
    codice_fornitore = fields.Char(
        string='Codice Fornitore',
        help='Codice identificativo del fornitore (DEPRECATO - campo nascosto)',
        groups='base.group_user',
    )

    codice_cliente = fields.Char(
        string='Codice Cliente',
        help='Codice identificativo del cliente (DEPRECATO - campo nascosto)',
        groups='base.group_user',
    )

    stato_cliente = fields.Selection([
        ('no_cons_diretta', 'NO Cons. Diretta'),
        ('nuovo', 'Nuovo'),
        ('sospeso', 'Sospeso'),
        ('storico', 'Storico'),
    ], string='Stato Cliente', help='Stato attuale del cliente')

    tipo_cliente = fields.Selection([
        ('dettaglio', 'DETTAGLIO'),
        ('gdo', 'GDO'),
        ('grossista', 'GROSSISTA'),
    ], string='Tipo Cliente', help='Tipologia del cliente')
    
    codice_prodotti_fornitore = fields.Char(
        string='Codice Prodotti Fornitore',
        help='Codice identificativo dei prodotti forniti dal fornitore (deve essere univoco)',
        groups='base.group_user',
    )

    @api.onchange('codice_prodotti_fornitore')
    def _onchange_codice_prodotti_fornitore(self):
        """Verifica che il codice prodotti fornitore sia univoco"""
        if self.codice_prodotti_fornitore and self.is_supplier:
            # Cerca altri fornitori con lo stesso codice
            domain = [
                ('codice_prodotti_fornitore', '=', self.codice_prodotti_fornitore),
                ('is_supplier', '=', True),
            ]
            # Esclude il record corrente se ha un ID
            if self._origin.id:
                domain.append(('id', '!=', self._origin.id))
            
            existing = self.env['res.partner'].search(domain, limit=1)
            if existing:
                return {
                    'warning': {
                        'title': _('Attenzione - Codice Duplicato'),
                        'message': _('Il Codice Prodotti Fornitore "%s" è già utilizzato dal fornitore "%s". Il codice deve essere univoco.') % (
                            self.codice_prodotti_fornitore, 
                            existing.name
                        ),
                    }
                }

    giorno_di_chiusura = fields.Char(
        string="Giorno di chiusura"
    )
    etichetta_telefono = fields.Char(
        string='Etichetta Tel. Fisso',
        help='Etichetta per il numero di telefono fisso',
        groups='base.group_user',
    )
    etichetta_cellulare = fields.Char(
        string='Etichetta Cellulare',
        help='Etichetta per il numero di cellulare',
        groups='base.group_user',
    )
    contact_method = fields.Selection([
        ('whatsapp', 'WhatsApp'),
        ('telefono', 'Telefono'),
        ('mail', 'Mail'),
    ], string='Metodo di contatto',
        help='Metodo preferito per contattare il partner',
        groups='base.group_user',
    )
    note_consegna = fields.Text(
        string='Note di Consegna',
        help='Note aggiuntive per la consegna',
        groups='base.group_user',
    )
    note_amministrative = fields.Text(
        string='Note Amministrative',
        help='Note aggiuntive per le pratiche amministrative',
        groups='base.group_user',
    )
    note_passaggi = fields.Text(
        string='Note di Passaggi',
        help='Note aggiuntive per i passaggi',
        groups='base.group_user',
    )
    listini_consegnati = fields.Char(
        string='Listini Consegnati',
        groups='base.group_user',
    )