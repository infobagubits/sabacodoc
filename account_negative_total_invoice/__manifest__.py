{
    "name": "Fatture con totale negativo",
    "summary": "Consente di registrare fatture clienti e fornitori con importo totale negativo",
    "description": """
Rimuove, per le aziende che lo abilitano, il blocco standard di Odoo che impedisce
di confermare una fattura (out_invoice / in_invoice) con importo totale negativo.

L'opzione si attiva in Contabilità > Configurazione > Impostazioni.
Note di credito, ricevute e registrazioni manuali non sono interessate.
    """,
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "license": "LGPL-3",
    "author": "Personalizzazione",
    "depends": ["account"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
