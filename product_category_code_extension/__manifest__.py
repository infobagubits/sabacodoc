{
    'name': 'Estensione Codici Categoria Prodotto',
    'version': '18.0.1.0.0',
    'sequence': 0,
    'category': 'Inventory/Inventory',
    'summary': 'Aggiunge campi codice, codice complessivo e livello per le categorie prodotto',
    'description': """
        Questo modulo estende il modello product.category aggiungendo:
        - Campo Codice (codice) - generato automaticamente
        - Campo Codice complessivo (codice completo) - calcolato basato sulla gerarchia
        - Campo Livello (livello) - calcolato basato sulla profondità nell'albero
        
        Funzionalità:
        - Generazione automatica di codici sequenziali
        - Calcolo automatico del livello gerarchico
        - Costruzione automatica del codice complessivo
        - Validazione contro gerarchie circolari
        - Aggiornamento a cascata quando la gerarchia cambia
        - Migrazione automatica per categorie esistenti
        - Azione per rigenerare tutti i codici
        
        Regole di generazione codici:
        - Livello 1: Codici basati sul nome della categoria
        - Con barra (/): Combina prima lettera prima e dopo la barra
        - Parole multiple: Prima lettera di ogni parola significativa
        - Parola singola: Prime due lettere
        - Livello 2-3: Codici numerici sequenziali (01, 02, 03...)
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['product'],
    'data': [
        'views/product_category_views.xml',
        # 'data/product_category_data.xml',  # Removido - dados de exemplo
        # 'data/migration_data.xml',         # Removido - migração automática
    ],
    'assets': {
        'web.assets_backend': [
            'product_category_code_extension/static/src/css/product_category.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
} 