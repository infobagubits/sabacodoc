{
    'name': 'Contact Customization',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Condicionais para campos de cliente e fornecedor',
    'description': """
        Este módulo adiciona condicionais para os campos de cliente e fornecedor
        baseado no módulo partner_customer_supplier_extension.
    """,
    'author': 'Bagubits Srls',
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