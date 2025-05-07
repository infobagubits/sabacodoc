{
    'name': 'Modulo Giri Ordini',
    'version': '18.0.1.0.0',
    'category': 'Uncategorized',
    'summary': 'Você terá uma tela exatamente igual a do Odoo, mas com a opção de escolher o dia da semana em que o pedido será entregue.',
    'sequence': '0',
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'mail', 'partner_customer_supplier_extension'],
    'data': [
        'views/giro_ordini_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'security/ir.model.access.csv',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
