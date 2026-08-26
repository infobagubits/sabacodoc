{
    'name': 'Modulo Giri Ordini',
    'version': '18.0.1.1.3',
    'category': 'Uncategorized',
    'summary': "Avrai una schermata esattamente uguale a quella di Odoo, ma con l'opzione di scegliere il giorno della settimana in cui l'ordine verrà consegnato.",
    'sequence': '0',
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['base', 'sale', 'mail', 'stock', 'partner_customer_supplier_extension', 'l10n_it_stock_ddt'],
    'data': [
        # La sicurezza va caricata per prima: la ACL e le view fanno riferimento ai gruppi
        'security/delivery_rounds_groups.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/giro_ordini_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/stock_picking_views.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
