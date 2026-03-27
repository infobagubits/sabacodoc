{
    'name': 'Sabaco - Documento Fornitore Stock Picking',
    'version': '18.0.1.0.0',
    'category': 'Inventario/Inventario',
    'summary': 'Aggiungi campi documento fornitore al trasferimento stock',
    'description': """
        Questo modulo aggiunge campi documento fornitore al trasferimento stock:
        - Numero Documento Fornitore (campo testo)
        - Data Documento Fornitore (campo data)
        
        Questi campi sono visibili solo per i trasferimenti in entrata (Ricezioni).
    """,
    'author': 'Bagubits SRLS',
    'depends': ['stock'],
    'data': [
        'views/stock_picking_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
} 