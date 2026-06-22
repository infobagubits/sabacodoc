{
    'name': 'Sabaco — Personalizzazione Pianificazione',
    'version': '18.0.1.3.5',
    'category': 'Human Resources/Planning',
    'summary': 'Ruolo prima di risorsa, filtro dipendenti e stampa PDF programma per ruolo',
    'description': """
        Personalizzazioni Pianificazione Sabaco:
        - Campo Ruolo prima di Risorsa nel form turno
        - Risorsa filtrata: solo dipendenti (resource_type=user) con il ruolo selezionato
        - Stampa PDF del programma per ruolo (layout Gantt giornaliero)
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'sequence': '0',
    'depends': ['planning'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/planning_schedule_print_wizard_views.xml',
        'report/planning_schedule_report_templates.xml',
        'views/planning_slot_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'sabaco_planning_customization/static/src/js/planning_gantt_print.js',
            'sabaco_planning_customization/static/src/xml/planning_gantt_print.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
