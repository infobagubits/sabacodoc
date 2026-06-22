{
    'name': 'IVA Differita (Italia)',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Gestione IVA differita su fatture fornitore',
    'description': """
        Aggiunge il campo "Iva differita" sulle fatture fornitore.
        Quando attivo:
        - Il conto Credito IVA viene sostituito con il conto IVA differita
        - Al momento della conferma viene creata automaticamente una registrazione
          nel giornale "Operazioni varie" con data l'ultimo giorno del mese precedente,
          che storna il conto IVA differita e accredita il Credito IVA.
    """,
    'author': 'Custom',
    'depends': ['account', 'l10n_it'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
