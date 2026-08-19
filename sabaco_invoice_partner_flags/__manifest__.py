{
    'name': 'Sabaco — Flag cliente/fornitore da fattura',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Alla conferma fattura vendita/fornitore marca is_customer/is_supplier sul contatto',
    'description': """
        Quando una fattura di vendita viene confermata (state=posted),
        imposta is_customer=True sul contatto (e sul commercial partner).

        Quando una fattura fornitore viene confermata,
        imposta is_supplier=True sul contatto (e sul commercial partner).

        Hook su write/create di account.move (state=posted), così copre
        action_post, _post e il wizard di conferma del core.
    """,
    'sequence': '0',
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'partner_customer_supplier_extension',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
