{
    'name': 'Sabaco Barcode Extension',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Estensione per visualizzazione note nei cards barcode operations',
    'description': """
        Modulo personalizzato per Sabaco che estende la visualizzazione 
        dei cards nella schermata Barcode Operations aggiungendo il campo note.
        
        FEATURES:
        - Visualizzazione campo note nei cards barcode operations
        - Supporto per dati personalizzati e dinamici
    """,
    'sequence': '0',
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': [
        'stock_barcode',
        'purchase_stock',
    ],
    'data': [
        'views/stock_barcode_picking_views.xml',
        'views/stock_picking_move_views.xml',
        'views/stock_move_line_product_selector.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sabaco_barcode_extension/static/src/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}

