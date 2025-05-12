{
    'name': 'Personalizzazione Contatti',
    'version': '1.0.1',
    'category': 'Sales/CRM',
    'summary': 'Condizionali per i campi cliente e fornitore',
    'description': """
        Questo modulo aggiunge condizionali per i campi cliente e fornitore
        basato sul modulo partner_customer_supplier_extension.
    """,
    'author': 'Il tuo nome',
    'website': 'https://www.seusite.com',
    'depends': ['base', 'contacts', 'partner_customer_supplier_extension'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 