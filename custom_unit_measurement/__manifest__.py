{
    'name': 'Custom Unit Measurement',
    'version': '18.0.1.3.0',
    'category': 'Inventory',
    'summary': 'Generic secondary unit of measure for products and stock management',
    'description': """
        Modulo generico per funzionalità di unità di misura secondaria:
        
        FEATURES:
        - Secondary unit of measure in products
        - Stock management with secondary units
        - Picking operations with secondary quantities
        - Stock quant tracking with secondary units
        - Automatic quantity calculations
        - Stock validation and controls
        
        This module provides a generic foundation that can be extended
        by other modules for specific business needs.
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['product', 'stock', 'mrp'],
    'data': [
        'views/product_template_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_move_line_secondary_operation_tree.xml',
        'views/stock_move_line_secondary_operations_list.xml',
        'views/stock_quant_views.xml',
        'views/stock_quant_simple_secondary_view.xml',
        'views/stock_scrap_views.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_production_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': '0',
}
