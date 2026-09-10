# -*- coding: utf-8 -*-
{
    'name': "Bank Reconciliation - Deferred Dates",
    'version': '18.0.1.0.0',
    'summary': "Data inizio / Data fine (risconto) nelle Operazioni manuali "
               "della riconciliazione bancaria (widget OWL)",
    'category': 'Accounting/Accounting',
    'author': "Tuo Nome",
    'depends': ['account_accountant'],
    # Nessun file 'data': la riconciliazione v18 non ha viste ir.ui.view,
    # l'intervento è tutto lato client (patch del template OWL).
    'assets': {
        'web.assets_backend': [
            'bank_rec_deferred_dates/static/src/bank_rec_form.xml',
        ],
    },
    'license': 'OEEL-1',
    'installable': True,
    'application': False,
}
