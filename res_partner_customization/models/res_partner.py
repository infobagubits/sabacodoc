from odoo import models, fields, api

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

    codice_fornitore = fields.Char(
        string='Codice Fornitore',
        help='Codice identificativo del fornitore',
        groups='base.group_user',
    )

    codice_cliente = fields.Char(
        string='Codice Cliente',
        help='Codice identificativo del cliente',
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

    giorno_di_chiusura = fields.Char(
        string="Giorno di chiusura",
        help="Inserisci il giorno di chiusura dell'azienda, se applicabile."
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
