{
    'name': 'IVA Differita (Italia)',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Gestione IVA differita su fatture fornitore',
    'description': """
        Aggiunge il campo "Iva differita" sulle fatture fornitore.

        La fattura va registrata direttamente dall'utente usando la tassa
        IVA differita (configurata con il proprio conto IVA differita e
        collegata, tramite il campo "Imposta originale", alla tassa che
        sostituisce, es. IVA 22%).

        Quando "Iva differita" è attivo, alla conferma della fattura:
        - i tag di griglia IVA vengono rimossi dalle righe, così che la
          fattura non compaia nella liquidazione IVA del mese corrente;
        - viene creata automaticamente una registrazione nel giornale
          "Operazioni varie", datata l'ultimo giorno del mese precedente,
          che gira l'importo dal conto IVA differita al Credito IVA
          originale (usando la tassa originale collegata).
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'depends': ['account', 'l10n_it'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
