{
    'name': 'Modulo Giri Ordini',
    'version': '18.0.1.0.2',
    'category': 'Uncategorized',

    'sequence': '0',
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'mail', 'stock', 'partner_customer_supplier_extension'],
    'data': [
        'views/giro_ordini_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
        'security/ir.model.access.csv',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
