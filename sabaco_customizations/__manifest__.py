{
    'name': 'Sabaco — Personalizzazioni',
    'version': '18.0.1.2.0',
    'category': 'Accounting',
    'summary': 'Personalizzazioni Sabaco (es. avviso totale fattura vs totale XML EDI)',
    'description': """
        Personalizzazioni trasversali per Sabaco:
        - Avviso su fatture fornitore e di vendita quando il totale Odoo
          differisce dal totale indicato nel file XML EDI (soma ImportoPagamento,
          come nel chatter).
        - Data fine registrazione differita impostata automaticamente uguale
          alla data inizio sulle righe fattura.
        - Avviso sulle registrazioni dei giornali dei corrispettivi quando il
          conto configurato non quadra (totale Dare diverso dal totale Avere).
        - Sincronizzazione bancaria online: per i movimenti di anticipo fatture
          (etichetta configurabile) la data della riga è il made_on dei
          dettagli operazione.
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'sequence': '0',
    'depends': ['account', 'account_accountant', 'account_online_synchronization', 'l10n_it_edi'],
    'data': [
        'data/ir_config_parameter.xml',
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
