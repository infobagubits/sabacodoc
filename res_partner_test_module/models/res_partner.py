from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Campos de teste para verificar atualização
    campo_teste_1 = fields.Char(
        string='Campo Teste 1',
        help='Campo de teste para verificar atualização',
        groups='base.group_user',
    )

    campo_teste_2 = fields.Selection([
        ('opcao1', 'Opção 1'),
        ('opcao2', 'Opção 2'),
        ('opcao3', 'Opção 3'),
    ], string='Campo Teste 2', help='Campo de seleção para teste')

    campo_teste_3 = fields.Text(
        string='Campo Teste 3',
        help='Campo de texto para teste',
        groups='base.group_user',
    )

    campo_teste_4 = fields.Boolean(
        string='Campo Teste 4',
        help='Campo booleano para teste',
        default=False,
    )

    campo_teste_5 = fields.Float(
        string='Campo Teste 5',
        help='Campo numérico para teste',
        digits=(16, 2),
    )

    # Campos do módulo original para teste
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
    
    codice_prodotti_fornitore = fields.Char(
        string='Codice Prodotti Fornitore',
        help='Codice identificativo dei prodotti forniti dal fornitore',
        groups='base.group_user',
    )

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
    
    contact_method_ids = fields.Many2many(
        'res.partner.contact_method',
        string='Metodi di contatto'
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
