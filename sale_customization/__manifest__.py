{
    'name': 'Modulo Personalizzato Vendite',
    'version': '18.0.1.0.0',
    'category': 'Sales/Inventory',
    'summary': 'Sales Customization for Sabaco - Advanced sales features and partner-specific functionality',
    'description': """
        Advanced sales customization module for Sabaco client:
        
        SALES CUSTOMIZATIONS:
        - Automatic loading of last 4 products sold to customer
        - Partner-specific packaging filtering
        - Read-only fields (price list, payment terms, UoM)
        - Packaging creation/navigation blocking
        - Secondary unit of measure integration in sales lines
        
        ADVANCED FEATURES:
        - Smart product selection: when customer is selected, 
          automatically loads last 4 products sold
        - Chronological management: products ordered by sale date
        - Duplicate prevention: each product appears only once
        - Optimized performance: search limited to recent products
        
        DEPENDENCIES:
        - Requires 'custom_unit_measurement' for secondary UoM functionality
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['product', 'stock', 'sale', 'sale_management', 'custom_unit_measurement'],
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': '0',
}
