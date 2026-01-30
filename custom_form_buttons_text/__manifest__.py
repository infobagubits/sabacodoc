{
    'name': 'Testo Pulsanti Modulo Personalizzato',
    'version': '18.0.1.0.0',
    'category': 'Web',
    'summary': 'Aggiunge testo ai pulsanti di azione del modulo (Salva, Scarta, Azioni)',
    'sequence': 1,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'description': """
        Questo modulo aggiunge testo descrittivo ai pulsanti di azione standard di Odoo:
        - Salva manualmente
        - Scarta tutte le modifiche
        - Azioni
        
        I testi appaiono accanto alle icone esistenti per una migliore usabilità.
        
        Implementazione tramite CSS (predefinito) o JavaScript (alternativa).
    """,
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'custom_form_buttons_text/static/src/scss/form_buttons_text.scss',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
} 