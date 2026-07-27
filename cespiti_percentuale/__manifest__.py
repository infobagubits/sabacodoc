{
    'name': 'Calcolo cespiti su base percentuale',
    'version': '18.0.1.1.0',
    'category': 'Accounting',
    'summary': (
        'Ammortamento cespiti con percentuale fiscale italiana (art. 102 TUIR): primo anno al 50%. '
        'Eccezione: conti cespite che iniziano per 03 usano la rata piena (100%) già dal primo anno.'
    ),
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'sequence': '0',
    'depends': ['account_asset'],
    'data': [
        'views/account_asset_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
