{
    'name': 'Sabaco — Personalizzazione Pianificazione',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Planning',
    'summary': 'Ruolo prima di risorsa e filtro dipendenti per ruolo nel turno',
    'description': """
        Personalizzazioni Pianificazione Sabaco:
        - Campo Ruolo prima di Risorsa nel form turno
        - Risorsa filtrata: solo dipendenti (resource_type=user) con il ruolo selezionato
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'sequence': '0',
    'depends': ['planning'],
    'data': [
        'views/planning_slot_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
