{
    'name': 'Italian EDI - PDF da XML Fattura Elettronica',
    'version': '1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Genera il PDF visivo della fattura elettronica italiana a partire dall\'XML EDI',
    'description': """
        Permette di generare il PDF ufficiale della fattura elettronica italiana
        applicando il foglio di stile XSLT (AssoSoftware) all'XML EDI già prodotto da Odoo.
        Il PDF viene salvato come allegato sulla fattura.
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'depends': ['l10n_it_edi', 'account'],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
