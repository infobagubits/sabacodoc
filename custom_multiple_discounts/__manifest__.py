{

    'name': 'Custom Multiple Discounts',
    'version': '18.0.1.0.0',
    'category': 'Uncategorized',
    'summary': 'Crea il campo sconti multipli e configura la pagina di vendita per ricevere la nuova funzionalità.',
    'sequence': '0',
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['sale'],
    'data': [
            'views/sale_config_settings_view.xml',
            'views/sale_order_line_view.xml',
            'views/sale_order_discount_wizard_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,

}
