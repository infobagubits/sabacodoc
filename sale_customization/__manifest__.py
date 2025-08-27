{
    'name': 'Modulo Personalizzato Vendite',
    'version': '18.0.1.0.0',
    'category': 'Sales/Inventory',
    'summary': 'Unità di misura secondaria nei prodotti + Personalizzazioni vendite',
    'description': """
        Modulo completo per personalizzazioni vendite e gestione unità secondaria:
        
        PERSONALIZZAZIONI VENDITE:
        - Rimuove il campo scadenza dalle vendite
        - Imposta listino prezzi in sola lettura
        - Imposta termini di pagamento in sola lettura
        - Imposta UdM in sola lettura nelle righe ordine
        - Blocca creazione e navigazione imballaggi
        - Aggiunge unità di misura secondaria nelle righe vendita
        - Caricamento automatico degli ultimi 4 prodotti venduti al cliente
        
        UNITÀ SECONDARIA:
        - Unità di misura secondaria nei prodotti
        - Gestione completa stock con unità secondaria
        - Controllo automatico disponibilità
        - Interfaccia integrata in picking e quant
        - Quantità secondaria nelle vendite
        
        FUNZIONALITÀ AVANZATE:
        - Selezione intelligente prodotti: quando si seleziona un cliente, 
          vengono automaticamente caricati gli ultimi 4 prodotti venduti
        - Gestione cronologica: i prodotti sono ordinati per data di vendita
        - Prevenzione duplicati: ogni prodotto appare una sola volta
        - Performance ottimizzata: ricerca limitata ai prodotti più recenti
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['product', 'stock', 'sale', 'sale_management'],
    'data': [
        'views/product_template_views.xml',
        'views/stock_picking_views.xml',
        'views/stock_move_line_secondary_operation_tree.xml',
        'views/stock_move_line_secondary_operations_list.xml',
        'views/stock_quant_views.xml',
        'views/stock_quant_simple_secondary_view.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'sequence': '0',
}
