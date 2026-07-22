{
    'name': 'Sabaco — UI contabilità',
    'version': '18.0.1.0.4',
    'category': 'Accounting',
    'summary': 'Miglioramenti interfaccia fatture e registrazioni (es. modifica massiva righe)',
    'description': """
        Personalizzazioni UI per la contabilità Sabaco:
        - modifica massiva e selezione multipla sulle righe fattura e sui movimenti
          contabili nel form della registrazione (stesso comportamento dell'elenco
          Contabilità → Movimenti contabili).
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'sequence': '0',
    'depends': ['account'],
    'data': [
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sabaco_account_ui/static/src/js/x2many_list_allow_selectors.js',
            'sabaco_account_ui/static/src/js/analytic_no_duplicates.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
