{
    'name': 'Sabaco — Personalizzazioni',
    'version': '18.0.1.0.3',
    'category': 'Accounting',
    'summary': 'Personalizzazioni Sabaco (es. avviso totale fattura vs totale XML EDI)',
    'description': """
        Personalizzazioni trasversali per Sabaco:
        - Avviso su fatture fornitore quando il totale Odoo differisce dal
          totale indicato nel file XML EDI (soma ImportoPagamento, come nel chatter).
        - Data fine registrazione differita impostata automaticamente uguale
          alla data inizio sulle righe fattura.
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'sequence': '0',
    'depends': ['account', 'account_accountant', 'l10n_it_edi'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
