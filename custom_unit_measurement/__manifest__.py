{
    'name': 'Unidade Secundária no Produto',
    'version': '1.0',
    'category': 'Inventory',
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['product', 'stock'],
    'data': [
        'views/product_template_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_move_line_secondary_operation_tree.xml',
        'views/stock_move_line_secondary_operations_list.xml',
        'views/stock_quant_views.xml',
        'views/stock_quant_simple_secondary_view.xml',



    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': '0',
}
