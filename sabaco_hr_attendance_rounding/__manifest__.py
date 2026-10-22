{
    'name': 'Sabaco — Arrotondamento timbrature presenze',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Attendances',
    'summary': "Arrotonda le timbrature alla mezz'ora: ingresso per eccesso, uscita per difetto",
    'description': """
        Le timbrature delle presenze vengono arrotondate alla mezz'ora (alle :00 o alle :30):
        - ingresso per eccesso alla mezz'ora successiva (08:17 -> 08:30; fino alle 08:00:59 resta 08:00);
        - uscita per difetto alla mezz'ora precedente (13:08 -> 13:00).
        Se l'uscita arrotondata cade prima dell'ingresso arrotondato la presenza risulta di 0 ore.

        Vale per tutte le timbrature (chiosco, app, inserimento e correzione manuale,
        uscita automatica); le ore lavorate e gli straordinari si calcolano sugli orari
        arrotondati. Non arrotonda le presenze tecniche create dal rilevamento assenze.
        Le timbrature già registrate non vengono modificate.
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': ['hr_attendance'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
