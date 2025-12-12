{
    'name': 'Personalizzazione Contatti',
    'version': '18.0.2.0.0',
    'category': 'Sales/CRM',
    'summary': 'Condizionali per i campi cliente e fornitore',
    'description': """
        Questo modulo aggiunge condizionali per i campi cliente e fornitore
        basato sul modulo partner_customer_supplier_extension.
    """,
    'sequence': 1,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts', 'account', 'partner_customer_supplier_extension'],
    'data': [
        'security/ir.model.access.csv',
        'data/contact_method_data.xml',
        'data/listino_data.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
} 