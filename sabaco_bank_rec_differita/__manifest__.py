{
    'name': 'Sabaco — Data differita nella riconciliazione bancaria',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Data inizio / fine differita sulle operazioni manuali della riconciliazione bancaria',
    'description': """
        Nella riconciliazione bancaria, sulle righe di costo o ricavo delle operazioni
        manuali, si possono indicare la data inizio e la data fine differita.
        Alla validazione vengono generate le registrazioni differite (risconti)
        come nelle fatture; al reset della riconciliazione vengono annullate e a una
        nuova validazione rigenerate, senza duplicati.

        Incompatibile con il modulo bank_rec_deferred_dates: l'installazione viene
        bloccata se quel modulo è installato.
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'OEEL-1',
    'depends': ['account_accountant'],
    'assets': {
        'web.assets_backend': [
            'sabaco_bank_rec_differita/static/src/bank_rec_form.xml',
        ],
    },
    'pre_init_hook': 'pre_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
