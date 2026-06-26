{
    "name": "Planning Gantt - Orari sulle barre (scala giorno)",
    "summary": "Scrive l'ora di inizio e fine sulle barre del Gantt del Planning nella scala giornaliera",
    "version": "18.0.2.0.0",
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    "category": "Human Resources/Planning",
    "depends": ["planning"],
    "assets": {
        "web.assets_backend": [
            "planning_gantt_pill_label/static/src/planning_gantt_pill_time.js",
            "planning_gantt_pill_label/static/src/planning_gantt_pill_time.css",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
