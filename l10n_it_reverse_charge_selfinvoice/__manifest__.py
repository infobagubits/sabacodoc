# -*- coding: utf-8 -*-
{
    "name": "Reverse Charge - Autofattura separata (IT)",
    "version": "18.0.1.5.0",
    "category": "Accounting/Localizations/Italy",
    "summary": "Doppia registrazione reverse charge: al post della fattura "
               "fornitore genera un'autofattura separata nel registro vendite "
               "(sezionale dedicato) e la collega alla fattura di origine.",
    "author": "Bagubits Srls",
    "website": "https://bagubits.it",
    "license": "LGPL-3",
    "depends": [
        "account",
        "l10n_it",
        "l10n_it_edi",
        "l10n_it_edi_ndd",
    ],
    "data": [
        "data/l10n_it_document_type_ensure.xml",
        "views/account_fiscal_position_views.xml",
        "views/account_tax_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
}
