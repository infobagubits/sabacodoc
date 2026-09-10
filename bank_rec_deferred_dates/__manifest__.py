# -*- coding: utf-8 -*-
{
    'name': "Bank Reconciliation - Deferred Dates",
    'version': '18.0.1.0.0',
    'summary': "Aggiunge Data inizio / Data fine (risconto) nelle "
               "Operazioni manuali della riconciliazione bancaria",
    'category': 'Accounting/Accounting',
    'author': "Tuo Nome",
    'depends': ['account_accountant'],
    'data': [
        'views/bank_rec_widget_views.xml',
    ],
    # account_accountant è Enterprise → licenza Enterprise
    'license': 'OEEL-1',
    'installable': True,
    'application': False,
}
