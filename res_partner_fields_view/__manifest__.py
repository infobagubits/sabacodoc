{
    'name': 'Partner Fields View Extension',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'View extension para campos específicos do partner',
    'description': """
        Este módulo adiciona apenas as views para campos específicos
        que não estão aparecendo no formulário de partner.
        Depende do res_partner_customization para os campos.
    """,
    'sequence': 1,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['base', 'contacts', 'res_partner_customization'],
    'data': [
        'views/res_partner_fields_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
