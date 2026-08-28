{
    'name': 'Azienda Customization',
    'version': '18.0.1.1.0',
    'category': 'Customizations',
    'summary': 'Customizzazioni generiche per Sabaco',
    'sequence': 1,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': [
        'product',
        'product_expiry',
        'stock',
    ],
    'data': [
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

