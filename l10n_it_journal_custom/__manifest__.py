# -*- coding: utf-8 -*-
{
    'name': 'Personalizzazione Registri Contabili Italiani',
    'version': '18.0.1.4',
    'sequence': '0',
    'category': 'Localizzazione/Italia',
    'summary': 'Personalizzazioni avanzate per "Registri IVA" e "Fatture Fornitore" - Layout dinamico, totali automatici, consolidamento imposte e customizzazioni specifiche',
    'description': """
        Modulo professionale per la personalizzazione dei registri contabili italiani
        
        CARATTERISTICHE PRINCIPALI
        =============================
        
        REGISTRI IVA:
        ================
        Header personalizzato dinamico su tutte le pagine
        Rimozione automatica della data dall'header standard
        Numerazione pagine con offset configurabile
        Titolo dinamico che riflette il nome del registro
        Informazioni aziendali complete nell'header
        Layout ottimizzato per stampa professionale
        
        TUTTI I REGISTRI:
        =====================
        Colonne ottimizzate (rimuove "Conto" e "Griglie Imposta")
        Totali automatici nella sezione "Imposta Applicata"
        Calcolo dinamico di: Importo Imponibile, Importo Imposta, Non Deducibile, Deducibile, In Scadenza
        Rimozione automatica sezione "Griglie Imposte Interessate"
        Layout pulito e professionale per tutti i tipi di registri
        CONSOLIDAMENTO AUTOMATICO: Impostos duplicados são agrupados e somados automaticamente
        
        CONFIGURAZIONE AVANZATA:
        ===========================
        - Accesso: Impostazioni → Contabilità → Report Italiani - Numerazione
        - Parametro 'l10n_it_custom.page_offset_enabled': Abilita numerazione personalizzata
        - Parametro 'l10n_it_custom.page_offset': Imposta numero pagina iniziale
        
        COMPATIBILITÀ:
        =================
        - Odoo Community/Enterprise 18.0+
        - Localizzazione italiana (l10n_it)
        - Modulo account_reports
        
        COMPORTAMENTO INTELLIGENTE:
        ==============================
        - REGISTRI IVA: Header personalizzato + colonne + totali
        - FATTURE FORNITORE: Colonne + totali personalizzati
        - TUTTI I REGISTRI: Colonne + totali personalizzati
        
    """,
    'author': 'Bagubits SRLS',
    'maintainer': 'Bagubits SRLS',
    'website': 'https://bagubits.it',
    'license': 'LGPL-3',
    'depends': [
        'base', 
        'account_reports', 
        'l10n_it'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/journal_report_templates.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3'
} 