{
    "name": "Sabaco Custom Reports",
    'version': '18.0.1.5.0',
    "summary": "Customize reports",
    "category": "Reporting",
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    "license": "LGPL-3",
    "depends": ["web", "sale_stock", "l10n_it_stock_ddt"],
    "data": [
        "views/external_layout_bubble.xml",
        "views/report_purchaseorder_document.xml",
        "views/report_saleorder_document.xml",
        "views/address_layout.xml",
        "views/report_invoice_document.xml",
        "views/report_ddt_document.xml",
    ],
    "installable": True,
    "application": False
}
