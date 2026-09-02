# -*- coding: utf-8 -*-

import io
from markupsafe import Markup
from odoo import models
from odoo.tools.misc import format_date
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class JournalReportCustomHandler(models.AbstractModel):
    _inherit = "account.journal.report.handler"

    def _get_vat_register_sign(self, move_type):
        """
        Segno contabile per i Registri IVA:
        - FA (fattura: out_invoice / in_invoice) → positivo
        - NC (nota di credito: out_refund / in_refund) → negativo
        """
        if move_type in ('out_refund', 'in_refund'):
            return -1.0
        return 1.0

    def _format_date_dd_mm_yyyy(self, date_value):
        """
        Formatta una data nel formato dd/mm/aaaa
        """
        try:
            if not date_value:
                return ''
            
            # Se è già una stringa nel formato corretto, restituisce
            if isinstance(date_value, str) and '/' in date_value:
                return date_value
            
            # Se è un oggetto datetime, converte
            if isinstance(date_value, datetime):
                return date_value.strftime('%d/%m/%Y')
            
            # Se è una stringa nel formato ISO (YYYY-MM-DD), converte
            if isinstance(date_value, str) and '-' in date_value:
                try:
                    dt = datetime.strptime(date_value, '%Y-%m-%d')
                    return dt.strftime('%d/%m/%Y')
                except ValueError:
                    pass
            
            # Fallback: tentare di convertire in datetime
            try:
                if hasattr(date_value, 'strftime'):
                    return date_value.strftime('%d/%m/%Y')
            except:
                pass
            
            _logger.warning(f"Errore nella formattazione della data: {date_value} (tipo: {type(date_value)})")
            return str(date_value) if date_value else ''
            
        except Exception as e:
            _logger.error(f"Errore nella formattazione della data: {e}")
            return str(date_value) if date_value else ''

    def _format_date_for_template(self, date_value):
        """
        Formatta una data nel formato dd/mm/aaaa per uso nei template QWeb
        """
        try:
            if not date_value:
                return ''
            
            # Usare la funzione format_date di Odoo con formato personalizzato
            return format_date(self.env, date_value, date_format='dd/MM/yyyy')
            
        except Exception as e:
            _logger.error(f"Errore nella formattazione della data per template: {e}")
            return str(date_value) if date_value else ''

    def _is_fatture_fornitore_report(self, options):
        """
        Rileva se il report corrente è specificamente per "Fatture Fornitore"
        basandosi sui registri selezionati (type = 'purchase')
        """
        try:
            if not options or not options.get('journals'):
                return False
            
            # Verifica se ci sono registri selezionati
            selected_journals = [j for j in options['journals'] if j.get('selected', False)]
            if not selected_journals:
                return False
            
            # Cerca i registri nel database per verificare il tipo
            journal_ids = [j['id'] for j in selected_journals if j.get('id')]
            if not journal_ids:
                return False
                
            journals = self.env['account.journal'].browse(journal_ids)
            
            # Se TUTTI i registri selezionati sono di tipo 'purchase', è "Fatture Fornitore"
            return all(journal.type == 'purchase' for journal in journals)
        except Exception as e:
            _logger.warning(f"Errore durante il rilevamento Fatture Fornitore: {e}")
            return False

    def _is_fatture_acquisti_eu_only(self, options):
        """
        Rileva se SOLAMENTE il registro "Fatture Acquisti EU" è selezionato
        
        :param options: Opzioni del report
        :return: True se solo "Fatture Acquisti EU" è selezionato, False altrimenti
        """
        try:
            if not options or not options.get('journals'):
                return False
            
            # Ottenere registri selezionati
            selected_journals = [j for j in options['journals'] if j.get('selected', False)]
            
            # Deve esserci ESATTAMENTE 1 registro selezionato
            if len(selected_journals) != 1:
                return False
            
            # E quel registro deve essere "Fatture Acquisti EU"
            journal_name = selected_journals[0].get('name', '')
            is_fatture_acquisti_eu = journal_name == "Fatture Acquisti EU"
            
            if is_fatture_acquisti_eu:
                _logger.info("🎯 Rilevato SOLO 'Fatture Acquisti EU'")
            
            return is_fatture_acquisti_eu
            
        except Exception as e:
            _logger.warning(f"Errore durante il rilevamento Fatture Acquisti EU: {e}")
            return False

    def _generate_document_data_for_export(self, report, options, export_type='pdf'):
        """
        Sovrascrive per rimuovere 'global_tax_summary' quando è Fatture Acquisti EU only
        """
        document_data = super()._generate_document_data_for_export(report, options, export_type)
        
        # ✅ RIMUOVI global_tax_summary quando è solo "Fatture Acquisti EU"
        if self._is_fatture_acquisti_eu_only(options):
            _logger.info("🎯 Fatture Acquisti EU: rimozione global_tax_summary")
            document_data['global_tax_summary'] = False
        
        return document_data

    def _get_columns_for_journal(self, journal, export_type='pdf'):
        """
        Sovrascrive il metodo originale per personalizzare le colonne per TUTTI i tipi di report
        ECCEZIONE: "Fatture Acquisti EU" usa layout PADRÃO
        """
        try:
            # Se non è PDF, utilizza comportamento standard
            if export_type != 'pdf':
                return super()._get_columns_for_journal(journal, export_type)
            
            # Verifica robusta del registro
            if not journal or not isinstance(journal, dict) or not journal.get('id'):
                return super()._get_columns_for_journal(journal, export_type)
            
            # Rileva il tipo di registro
            current_journal = self.env['account.journal'].browse(journal.get('id'))
            if not current_journal.exists():
                return super()._get_columns_for_journal(journal, export_type)
            
            # ✅ ECCEZIONE: "Fatture Acquisti EU" usa layout PADRÃO
            if current_journal.name == "Fatture Acquisti EU":
                _logger.info("🎯 Fatture Acquisti EU: utilizzo colonne PADRÃO Odoo")
                return super()._get_columns_for_journal(journal, export_type)
            
            # ✅ COLONNE PERSONALIZZATE per altri registri
            columns = [
                {'name': 'Data contabile', 'label': 'accounting_date'},
                {'name': 'Nº registro', 'label': 'move_name'},
                {'name': 'Causale', 'label': 'causale'},
                {'name': 'Data fattura', 'label': 'invoice_date'},
                {'name': 'Ref fattura', 'label': 'invoice_ref'},
                {'name': 'Ragione sociale\n\nDescrizione imposta', 'label': 'partner_name'},
                {'name': 'P.IVA/CF\n\nImponibile', 'label': 'partner_vat'},
                {'name': 'Totale fattura\n\nImposta', 'label': 'total_amount', 'class': 'o_right_alignment'},
            ]
            _logger.info(f"Applicazione colonne personalizzate per registro tipo: {current_journal.type}")
            return columns
                
        except Exception as e:
            _logger.warning(f"Errore in _get_columns_for_journal: {e}, utilizzo comportamento standard")
            return super()._get_columns_for_journal(journal, export_type)

    def _get_tax_summary_section(self, options, journal_vals=None):
        """
        Sovrascrive il metodo originale per aggiungere totali nella sezione "Imposta Applicata" 
        per TUTTI i tipi di report e rimuovere la sezione "Griglie Imposte Interessate"
        """
        try:
            # Chiama prima il metodo originale
            tax_summary = super()._get_tax_summary_section(options, journal_vals)
            
            # Rileva il tipo di registro
            journal_type = 'unknown'
            if journal_vals and journal_vals.get('type'):
                journal_type = journal_vals.get('type')
            
            # ✅ APPLICA PERSONALIZZAZIONI per TUTTI i tipi di registri
            _logger.info(f"Applicazione personalizzazioni per registro tipo: {journal_type}")
            
            # ✅ RIMUOVI SEZIONE "GRIGLIE IMPOSTE INTERESSATE" per tutti i tipi
            if 'tax_grid_summary_lines' in tax_summary:
                tax_summary['tax_grid_summary_lines'] = {}
                _logger.info(f"Sezione 'Griglie Imposte Interessate' rimossa per registro tipo: {journal_type}")
            
            # Se ci sono dati di imposte, calcola totali per TUTTI i tipi
            if tax_summary.get('tax_report_lines'):
                tax_lines = tax_summary['tax_report_lines']
                
                _logger.info(f"=== DEBUG TOTALI PER REGISTRO TIPO: {journal_type} ===")
                _logger.info(f"Struttura righe imposte: {tax_lines}")
                
                # Calcola totali per ogni colonna
                totals = {
                    'total_base_amount': 0.0,
                    'total_tax_amount': 0.0,
                    'total_non_deductible': 0.0,
                    'total_deductible': 0.0,
                    'total_due': 0.0
                }
                
                report = self.env['account.report'].browse(options['report_id'])
                
                # Somma tutti i valori per paese/imposta
                for country_name, country_taxes in tax_lines.items():
                    _logger.info(f"Elaborazione paese: {country_name}")
                    for tax in country_taxes:
                        _logger.info(f"Dati imposta: {tax}")
                        
                        # Funzione per convertire valore in float in modo sicuro
                        def safe_get_float(tax_dict, key_no_format, key_formatted=''):
                            # Priorità ai valori _no_format (più precisi)
                            if key_no_format in tax_dict:
                                val = tax_dict[key_no_format]
                                _logger.info(f"Utilizzo {key_no_format}: {val} (tipo: {type(val)})")
                                return float(val) if val is not None else 0.0
                            # Fallback per valore formattato
                            elif key_formatted and key_formatted in tax_dict:
                                formatted_val = tax_dict[key_formatted]
                                _logger.info(f"Utilizzo formattato {key_formatted}: {formatted_val}")
                                try:
                                    # Rimuovi simboli e converti (europeo: virgola come decimale)
                                    val_str = str(formatted_val).replace('€', '').replace(' ', '').strip()
                                    
                                    # Gestione formato europeo: punto come separatore di migliaia, virgola come decimale
                                    if ',' in val_str and '.' in val_str:
                                        # Formato: 1.234,56 -> 1234.56
                                        # Rimuovi i punti (separatori di migliaia) e sostituisci virgola con punto
                                        val_str = val_str.replace('.', '').replace(',', '.')
                                    elif ',' in val_str and val_str.count(',') == 1:
                                        # Formato: 1234,56 -> 1234.56 (solo virgola decimale)
                                        val_str = val_str.replace(',', '.')
                                    # Se ha solo punti, potrebbe essere formato americano o europeo
                                    elif '.' in val_str and ',' not in val_str:
                                        # Conta i punti per determinare se sono separatori di migliaia
                                        dot_count = val_str.count('.')
                                        if dot_count > 1:
                                            # Formato europeo: 1.234.567 -> 1234567
                                            val_str = val_str.replace('.', '')
                                        # Se ha solo un punto, potrebbe essere decimale americano, lasciare così
                                    
                                    result = float(val_str) if val_str else 0.0
                                    _logger.info(f"Convertito in: {result}")
                                    return result
                                except (ValueError, TypeError) as e:
                                    _logger.warning(f"Errore conversione {formatted_val}: {e}")
                                    return 0.0
                            _logger.info(f"Nessun valore trovato per {key_no_format}/{key_formatted}")
                            return 0.0
                        
                        # Somma valori utilizzando campi _no_format quando disponibili
                        base_val = safe_get_float(tax, 'base_amount_no_format', 'base_amount')
                        tax_val = safe_get_float(tax, 'tax_amount_no_format', 'tax_amount')
                        non_ded_val = safe_get_float(tax, 'tax_non_deductible_no_format', 'tax_non_deductible')
                        ded_val = safe_get_float(tax, 'tax_deductible_no_format', 'tax_deductible')
                        due_val = safe_get_float(tax, 'tax_due_no_format', 'tax_due')
                        
                        # DEBUG: Log dei valori prima della somma
                        _logger.info(f"VALORI PRIMA DELLA SOMMA - Base: {base_val}, Imposta: {tax_val}")
                        _logger.info(f"TOTALI PRIMA - Base: {totals['total_base_amount']}, Imposta: {totals['total_tax_amount']}")
                        
                        totals['total_base_amount'] += base_val
                        totals['total_tax_amount'] += tax_val
                        totals['total_non_deductible'] += non_ded_val
                        totals['total_deductible'] += ded_val
                        totals['total_due'] += due_val
                        
                        # DEBUG: Log dei valori dopo la somma
                        _logger.info(f"VALORI DOPO LA SOMMA - Base: {base_val}, Imposta: {tax_val}")
                        _logger.info(f"TOTALI DOPO - Base: {totals['total_base_amount']}, Imposta: {totals['total_tax_amount']}")
                        _logger.info(f"Aggiunti - Base: {base_val}, Imposta: {tax_val}, NonDed: {non_ded_val}, Ded: {ded_val}, Scadenza: {due_val}")
                
                _logger.info(f"Totali finali: {totals}")
                
                # Formatta i totali per la visualizzazione
                tax_summary['totals'] = {
                    'total_base_amount': report._format_value(options, totals['total_base_amount'], 'monetary'),
                    'total_tax_amount': report._format_value(options, totals['total_tax_amount'], 'monetary'),
                    'total_non_deductible': report._format_value(options, totals['total_non_deductible'], 'monetary'),
                    'total_deductible': report._format_value(options, totals['total_deductible'], 'monetary'),
                    'total_due': report._format_value(options, totals['total_due'], 'monetary'),
                }
                
                _logger.info(f"Totali formattati per registro tipo {journal_type}: {tax_summary['totals']}")
            
            return tax_summary
            
        except Exception as e:
            _logger.error(f"Errore in _get_tax_summary_section personalizzato: {e}")
            return super()._get_tax_summary_section(options, journal_vals)

    def _get_export_lines_for_journal(self, report, options, export_type, journal_vals, account_move_vals_list):
        """
        Sovrascrive il metodo per mostrare righe principali + righe di impostos
        Filtra le righe di dettaglio mantenendo solo:
        - j == 0: Nome del documento (riga principale)
        - Aggiunge righe di impostos sotto ogni riga principale
        ECCEZIONE: "Fatture Acquisti EU" usa layout PADRÃO
        """
        try:
            # ✅ ECCEZIONE: "Fatture Acquisti EU" usa layout PADRÃO
            if journal_vals.get('name') == "Fatture Acquisti EU":
                _logger.info("🎯 Fatture Acquisti EU: utilizzo righe PADRÃO Odoo")
                return super()._get_export_lines_for_journal(report, options, export_type, journal_vals, account_move_vals_list)
            
            _logger.info(f"Filtrando righe per mostrare principali + impostos per registro tipo: {journal_vals.get('type')}")
            
            lines = []
            
            if journal_vals['type'] == 'bank':
                return self._get_export_lines_for_bank_journal(report, options, export_type, journal_vals, account_move_vals_list)

            total_credit = 0
            total_debit = 0

            for i, account_move_line_vals_list in enumerate(account_move_vals_list):
                # ✅ PROCESSARE SOLO la PRIMA RIGA (j == 0) - riga principale/totalizzatrice
                if len(account_move_line_vals_list) > 0:
                    move_line_entry_vals = account_move_line_vals_list[0]  # Solo prima riga
                    document = move_line_entry_vals['move_name']
                    
                    # ✅ RIGA PRINCIPALE
                    line = self._get_custom_base_line(report, options, export_type, document, move_line_entry_vals, i, i % 2 != 0, journal_vals.get('tax_summary'))
                    
                    total_credit += move_line_entry_vals['credit']
                    total_debit += move_line_entry_vals['debit']
                    
                    lines.append(line)
                    _logger.info(f"Riga principale aggiunta: {document}")
                    
                    # ✅ RIGHE DI IMPOSTOS - Aggiungere sotto ogni riga principale
                    # Passa anche l'informazione se la riga è dispari (cinza) o pari (bianca)
                    tax_lines = self._get_tax_lines_for_move(report, options, export_type, move_line_entry_vals, i, i % 2 != 0)
                    if tax_lines:
                        lines.extend(tax_lines)
                        _logger.info(f"Aggiunte {len(tax_lines)} righe di impostos per: {document}")

            _logger.info(f"Totale righe filtrate: {len(lines)} (principali + impostos)")
            return lines
            
        except Exception as e:
            _logger.error(f"Errore in _get_export_lines_for_journal personalizzato: {e}")
            return super()._get_export_lines_for_journal(report, options, export_type, journal_vals, account_move_vals_list)

    def _get_custom_base_line(self, report, options, export_type, document, move_line_entry_vals, j, is_uneven_line, tax_summary):
        """
        Metodo personalizzato per creare riga base con le nuove colonne:
        - Data Fattura
        - Numero Fattura  
        - Causale (NC/FA)
        - Linhas de impostos abaixo de cada linha principal
        """
        try:
            # Prima ottenere la riga base standard
            base_line = self._get_base_line(report, options, export_type, document, move_line_entry_vals, j, is_uneven_line, tax_summary)
            
            # Estrarre dati aggiuntivi da move_line_entry_vals
            move_data = move_line_entry_vals
            
            # ✅ ESTRARRE DATA DELLA FATTURA basato sul codice sorgente Odoo
            invoice_date = ''
            if 'date' in move_data and move_data['date']:
                invoice_date = self._format_date_dd_mm_yyyy(move_data['date'])
            
            # ✅ ESTRARRE NUMERO DELLA FATTURA basato sul codice sorgente Odoo
            invoice_number = ''
            if 'move_name' in move_data and move_data['move_name']:
                invoice_number = str(move_data['move_name'])
            
            # ✅ DETERMINARE CAUSALE basato sul campo move_type
            causale = 'FA'  # Default: Fattura
            
            # Debug: mostrare tutti i campi disponibili
            _logger.info(f"=== DEBUG MOVE_DATA ===")
            _logger.info(f"Campi disponibili: {list(move_data.keys())}")
            _logger.info(f"Valori completi: {move_data}")
            
            # Tentare diverse forme di accedere al move_type
            move_type = None
            
            # 1. Tentare direttamente
            if 'move_type' in move_data:
                move_type = move_data['move_type']
                _logger.info(f"Move type trovato direttamente: {move_type}")
            
            # 2. Tentare di accedere via move_id se disponibile
            elif 'move_id' in move_data and move_data['move_id']:
                try:
                    move_record = self.env['account.move'].browse(move_data['move_id'])
                    if move_record.exists():
                        move_type = move_record.move_type
                        _logger.info(f"Move type ottenuto via move_id: {move_type}")
                except Exception as e:
                    _logger.warning(f"Errore nell'ottenere move_type via move_id: {e}")
            
            # 3. Tentare di accedere via parent se disponibile
            elif 'parent' in move_data and move_data['parent']:
                parent_data = move_data['parent']
                if 'move_type' in parent_data:
                    move_type = parent_data['move_type']
                    _logger.info(f"Move type trovato in parent: {move_type}")
            
            # Applicare logica della causale
            if move_type:
                if move_type in ['out_invoice', 'in_invoice']:
                    causale = 'FA'  # Fattura
                elif move_type in ['out_refund', 'in_refund']:
                    causale = 'NC'  # Nota di Credito
                else:
                    causale = 'FA'  # Default per altri tipi
                _logger.info(f"Causale determinata: {causale} per move_type: {move_type}")
            else:
                _logger.warning(f"Move type non trovato in nessuna localizzazione")
                # Fallback: tentare di determinare per riferimento o nome
                if 'reference' in move_data and move_data['reference']:
                    ref_lower = str(move_data['reference']).lower()
                    if any(keyword in ref_lower for keyword in ['credit', 'nc', 'nota', 'refund']):
                        causale = 'NC'
                        _logger.info(f"Causale determinata per riferimento: {causale}")
            
            # ✅ AGGIUNGERE LE NUOVE COLONNE direttamente nella struttura della riga
            
            # 1. DATA CONTABILE (accounting_date)
            accounting_date = ''
            if 'date' in move_data and move_data['date']:
                accounting_date = self._format_date_dd_mm_yyyy(move_data['date'])
            
            base_line['accounting_date'] = {
                'data': accounting_date,
                'class': 'text-center'
            }
            
            # 2. Nº REGISTRO (move_name)
            move_name = move_data.get('move_name', 'N/A')
            base_line['move_name'] = {
                'data': move_name,
                'class': 'text-center'
            }
            
            # 3. CAUSALE (già implementata)
            base_line['causale'] = {
                'data': causale,
                'class': 'text-center font-weight-bold'
            }
            
            # 4. DATA FATTURA (invoice_date)
            base_line['invoice_date'] = {
                'data': invoice_date or accounting_date,  # Usare data contabile se non c'è data fattura
                'class': 'text-center'
            }
            
            # 5. REF FATTURA (invoice_ref)
            invoice_ref = move_data.get('reference', '') or move_data.get('invoice_ref', '')
            base_line['invoice_ref'] = {
                'data': invoice_ref,
                'class': 'text-center'
            }
            
            # 6. RAGIONE SOCIALE (partner_name)
            partner_name = move_data.get('partner_name', 'N/A')
            base_line['partner_name'] = {
                'data': partner_name,
                'class': 'text-left'
            }
            
            # ✅ ESTRARRE P.IVA FORNITORE
            partner_vat = ''
            
            # Debug: mostrare dati disponibili
            _logger.info(f"=== DEBUG P.IVA FORNITORE ===")
            _logger.info(f"Campi disponibili in move_data: {list(move_data.keys())}")
            _logger.info(f"partner_id: {move_data.get('partner_id')}")
            _logger.info(f"partner_name: {move_data.get('partner_name')}")
            
            # 1. Tentare di ottenere via partner_id (metodo principale)
            if 'partner_id' in move_data and move_data['partner_id']:
                try:
                    partner_record = self.env['res.partner'].browse(move_data['partner_id'])
                    if partner_record.exists():
                        # Priorità: vat (Tax ID) -> l10n_it_codice_fiscale -> vat_number
                        partner_vat = (partner_record.vat or 
                                     partner_record.l10n_it_codice_fiscale or 
                                     getattr(partner_record, 'vat_number', '') or '')
                        _logger.info(f"P.IVA via partner_id {move_data['partner_id']}: '{partner_vat}'")
                        _logger.info(f"Partner name: {partner_record.name}")
                        _logger.info(f"Partner vat: {partner_record.vat}")
                        _logger.info(f"Partner l10n_it_codice_fiscale: {partner_record.l10n_it_codice_fiscale}")
                except Exception as e:
                    _logger.warning(f"Errore nell'ottenere P.IVA via partner_id: {e}")
            
            # 2. Fallback: tentare di ottenere via campi diretti nei dati del movimento
            if not partner_vat:
                partner_vat = (move_data.get('partner_vat', '') or 
                             move_data.get('partner_fiscal_code', '') or
                             move_data.get('vat', '') or '')
                _logger.info(f"P.IVA via campi diretti: '{partner_vat}'")
            
            # 3. Se ancora non trovato, tentare via partner_name (ricerca)
            if not partner_vat and 'partner_name' in move_data and move_data['partner_name']:
                try:
                    partner_name = move_data['partner_name']
                    partner_search = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
                    if partner_search:
                        partner_vat = partner_search.vat or partner_search.l10n_it_codice_fiscale or ''
                        _logger.info(f"P.IVA via ricerca per nome '{partner_name}': '{partner_vat}'")
                except Exception as e:
                    _logger.warning(f"Errore nella ricerca per nome del partner: {e}")
            
            # 7. VAT/CF (partner_vat)
            base_line['partner_vat'] = {
                'data': partner_vat or 'N/A',
                'class': 'text-center'
            }
            
            # 8. TOTALE FATTURA (amount_total) - Modificato da imponibile a totale
            # Cercare il valore totale direttamente dal registro account.move
            total_amount = 0.0
            
            # 1. Tentare di ottenere via move_id (metodo principale)
            if 'move_id' in move_data and move_data['move_id']:
                try:
                    move_record = self.env['account.move'].browse(move_data['move_id'])
                    if move_record.exists():
                        # Usare amount_total (valore totale della fattura)
                        total_amount = move_record.amount_total or 0
                        _logger.info(f"Totale fattura via amount_total: {total_amount}")
                        
                        # Debug: mostrare altri valori per confronto
                        _logger.info(f"Move record: {move_record.name}")
                        _logger.info(f"amount_untaxed: {move_record.amount_untaxed}")
                        _logger.info(f"amount_total: {move_record.amount_total}")
                        _logger.info(f"amount_tax: {move_record.amount_tax}")
                        
                except Exception as e:
                    _logger.warning(f"Errore nell'ottenere totale via move_id: {e}")
            
            # 2. Fallback: usare campi diretti se non riuscito via move_id
            if total_amount == 0:
                # Tentare campi alternativi per totale
                total_amount = (move_data.get('amount_total', 0) or 
                              move_data.get('total_amount', 0) or 
                              move_data.get('credit', 0) or 0)
                _logger.info(f"Totale fattura via campi alternativi: {total_amount}")

            # Segno FA+/NC- coerente con le righe imponibile/imposta
            sign = self._get_vat_register_sign(move_type) if move_type else (
                -1.0 if causale == 'NC' else 1.0
            )
            total_amount = abs(float(total_amount or 0.0)) * sign
            
            base_line['total_amount'] = {
                'data': report._format_value(options, total_amount, 'monetary'),
                'class': 'o_right_alignment'
            }
            
            _logger.info(f"P.IVA finale per colonna: '{partner_vat or 'N/A'}'")
            _logger.info(f"Totale fattura finale: {total_amount}")
            
            return base_line
            
        except Exception as e:
            _logger.error(f"Errore in _get_custom_base_line: {e}")
            # Fallback per metodo standard
            return self._get_base_line(report, options, export_type, document, move_line_entry_vals, j, is_uneven_line, tax_summary)

    def _get_tax_lines_for_move(self, report, options, export_type, move_line_entry_vals, move_index, is_uneven_line):
        """
        Estrae e formatta le righe di impostos per un movimento specifico
        AGRUPA e SOMA impostos com o mesmo nome (consolidação)
        INCLUDE impostos com alíquota 0% (modificato per mostrare anche IVA 0%)
        Restituisce una lista di righe formattate per gli impostos consolidati
        """
        try:
            tax_lines = []
            move_data = move_line_entry_vals
            
            # ✅ ESTRARRE IMPOSTOS dal movimento
            if 'move_id' in move_data and move_data['move_id']:
                try:
                    move_record = self.env['account.move'].browse(move_data['move_id'])
                    if move_record.exists():
                        _logger.info(f"=== DEBUG IMPOSTOS PER MOVE {move_record.name} ===")

                        # FA = importi positivi; NC = importi negativi (Registri IVA)
                        sign = self._get_vat_register_sign(move_record.move_type)
                        
                        # ✅ STRATEGIA COMBINATA: Ottenere impostos sia dalle tax_lines che dalle invoice_lines
                        tax_consolidated = {}
                        
                        # METODO 1: Ottenere righe di imposta già create (tax_line_id)
                        tax_lines_data = move_record.line_ids.filtered(lambda l: l.tax_line_id)
                        
                        if tax_lines_data:
                            _logger.info(f"Trovate {len(tax_lines_data)} righe di imposta con tax_line_id")
                            
                            for tax_line in tax_lines_data:
                                tax_name = tax_line.tax_line_id.name if tax_line.tax_line_id else 'Imposta'
                                # abs + segno: evita base negativa su FA e forza il meno sulle NC
                                tax_amount = abs(tax_line.credit or tax_line.debit or 0.0) * sign
                                tax_base = abs(tax_line.tax_base_amount or 0.0) * sign
                                
                                _logger.info(f"Processando (tax_line): {tax_name}, Base: {tax_base}, Importo: {tax_amount}, sign={sign}")
                                
                                if tax_name in tax_consolidated:
                                    tax_consolidated[tax_name]['tax_amount'] += tax_amount
                                    _logger.info(f"Somado valor do imposto: {tax_name}")
                                else:
                                    tax_consolidated[tax_name] = {
                                        'tax_name': tax_name,
                                        'tax_amount': tax_amount,
                                        'tax_base': tax_base
                                    }
                        
                        # METODO 2: ✅ AGGIUNGERE impostos con aliquota 0% dalle invoice_lines
                        # Questi impostos potrebbero non avere tax_line_id perché Odoo li rimuove se valore = 0
                        if move_record.invoice_line_ids:
                            _logger.info(f"Analizzando {len(move_record.invoice_line_ids)} invoice_lines per impostos 0%")
                            
                            for inv_line in move_record.invoice_line_ids:
                                if inv_line.tax_ids:
                                    _logger.info(f"Linea fattura: {inv_line.name}, Impostos applicati: {len(inv_line.tax_ids)}")
                                    
                                    for tax in inv_line.tax_ids:
                                        tax_name = tax.name
                                        
                                        # Se questo imposto NON è già presente nel consolidato
                                        # significa che è un imposto a 0% che non ha generato tax_line
                                        if tax_name not in tax_consolidated:
                                            _logger.info(f"Trovato imposto 0% non in consolidato: {tax_name}")
                                            
                                            # Calcolare base imponibile per questo imposto
                                            # Base = prezzo_totale della riga (price_subtotal)
                                            tax_base = abs(inv_line.price_subtotal or 0.0) * sign
                                            
                                            # Valor do imposto será sempre 0 se não foi criado tax_line
                                            tax_amount = 0.0
                                            
                                            tax_consolidated[tax_name] = {
                                                'tax_name': tax_name,
                                                'tax_amount': tax_amount,
                                                'tax_base': tax_base
                                            }
                                            _logger.info(f"Aggiunto imposto 0%: {tax_name} - Base: {tax_base}, Importo: {tax_amount}")
                        
                        _logger.info(f"Consolidamento completato: {len(tax_consolidated)} impostos únicos (inclusi 0%)")
                        
                        # ✅ CRIAR LINHAS CONSOLIDADAS (inclui impostos 0%)
                        for tax_name, tax_data in tax_consolidated.items():
                            tax_info = self._format_consolidated_tax_line(
                                report, 
                                options, 
                                tax_data, 
                                move_index, 
                                is_uneven_line
                            )
                            if tax_info:
                                tax_lines.append(tax_info)
                                _logger.info(f"Riga consolidata aggiunta: {tax_name} - Base: {tax_data['tax_base']}, Importo: {tax_data['tax_amount']}")
                        
                        if not tax_consolidated:
                            _logger.info("Nessuna riga di imposta trovata per questo movimento")
                            
                except Exception as e:
                    _logger.warning(f"Errore nell'estrarre impostos per move_id {move_data['move_id']}: {e}")
            
            return tax_lines
            
        except Exception as e:
            _logger.error(f"Errore in _get_tax_lines_for_move: {e}")
            return []

    def _format_consolidated_tax_line(self, report, options, tax_data, move_index, is_uneven_line):
        """
        Formatta una riga consolidata di imposta per il report
        Usado para linhas de imposto agrupadas e somadas
        """
        try:
            # ✅ ESTRARRE DATI CONSOLIDATI
            tax_name = tax_data.get('tax_name', 'Imposta')
            tax_amount = tax_data.get('tax_amount', 0)
            tax_base = tax_data.get('tax_base', 0)
            
            _logger.info(f"Formatando linha consolidada - Imposta: {tax_name}, Base: {tax_base}, Importo: {tax_amount}")
            
            # ✅ DETERMINARE CLASSE per colore di sfondo
            # Se la riga principale è dispari (cinza), anche le righe di imposta devono essere cinza
            # o_even = cinza, o_odd = bianco (conforme CSS Odoo)
            background_class = 'o_even' if is_uneven_line else 'o_odd'
            
            # ✅ CREARE RIGA VUOTA per impostos (prime 5 colonne vuote)
            tax_line_data = {
                'line_class': background_class,  # Classe per tutta la riga
                'accounting_date': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'move_name': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'causale': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'invoice_date': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'invoice_ref': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'partner_name': {
                    'data': tax_name,  # Nome dell'imposta consolidata
                    'class': 'text-left'
                },
                'partner_vat': {
                    'data': report._format_value(options, tax_base, 'monetary'),  # Base imponibile consolidata
                    'class': 'text-center'
                },
                'total_amount': {
                    'data': report._format_value(options, tax_amount, 'monetary'),  # Importo imposta consolidato
                    'class': 'o_right_alignment'
                }
            }
            
            _logger.info(f"Riga consolidata formattata con classe: {background_class} (is_uneven_line: {is_uneven_line})")
            
            return tax_line_data
            
        except Exception as e:
            _logger.error(f"Errore in _format_consolidated_tax_line: {e}")
            return None

    def _format_tax_line_for_report(self, report, options, tax_line, move_index, is_uneven_line):
        """
        Formatta una singola riga di imposta per il report
        NOTA: Este método agora é OBSOLETO - usar _format_consolidated_tax_line
        Mantido para compatibilidade com código legado
        """
        try:
            # ✅ ESTRARRE DATI DELL'IMPOSTA (FA+/NC-; metodo legacy)
            tax_name = tax_line.tax_line_id.name if tax_line.tax_line_id else 'Imposta'
            sign = self._get_vat_register_sign(tax_line.move_id.move_type if tax_line.move_id else False)
            tax_amount = abs(tax_line.credit or tax_line.debit or 0.0) * sign
            tax_base = abs(tax_line.tax_base_amount or 0.0) * sign
            
            _logger.info(f"Imposta: {tax_name}, Base: {tax_base}, Importo: {tax_amount}, sign={sign}")
            
            # ✅ DETERMINARE CLASSE per colore di sfondo
            # Se la riga principale è dispari (cinza), anche le righe di imposta devono essere cinza
            # o_even = cinza, o_odd = bianco (conforme CSS Odoo)
            background_class = 'o_even' if is_uneven_line else 'o_odd'
            
            # ✅ CREARE RIGA VUOTA per impostos (prime 5 colonne vuote)
            tax_line_data = {
                'line_class': background_class,  # Classe per tutta la riga
                'accounting_date': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'move_name': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'causale': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'invoice_date': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'invoice_ref': {
                    'data': '',  # Vuoto
                    'class': 'text-center'
                },
                'partner_name': {
                    'data': tax_name,  # Nome dell'imposta
                    'class': 'text-left'
                },
                'partner_vat': {
                    'data': report._format_value(options, tax_base, 'monetary'),  # Base imponibile
                    'class': 'text-center'
                },
                'total_amount': {
                    'data': report._format_value(options, tax_amount, 'monetary'),  # Importo imposta
                    'class': 'o_right_alignment'
                }
            }
            
            _logger.info(f"Riga imposta formattata con classe: {background_class} (is_uneven_line: {is_uneven_line})")
            
            return tax_line_data
            
        except Exception as e:
            _logger.error(f"Errore in _format_tax_line_for_report: {e}")
            return None

    def _export_to_pdf_fatture_acquisti_eu(self, options, report):
        """
        Metodo specifico per "Fatture Acquisti EU":
        - Usa template PADRÃO Odoo per body (colunas, linhas)
        - Usa footer CUSTOMIZZATO (paginazione con offset)
        - RIMUOVE "Riepilogo Generale Imposte" (global_tax_summary)
        - MANTIENE totali customizzati nella sezione "Imposta Applicata"
        """
        _logger.info("🎯 Generando PDF per Fatture Acquisti EU con paginazione customizzata")
        
        base_url = report.get_base_url()
        print_options = {
            **report.get_options(previous_options={**options, 'export_mode': 'print'}),
            'css_custom_class': self._get_custom_display_config().get('pdf_css_custom_class', 'journal_report_pdf')
        }
        
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
            'options': print_options,
            'report': report,
            'format_date_dd_mm_yyyy': self._format_date_for_template,
        }
        
        # ✅ FOOTER CUSTOMIZZATO (paginazione con offset)
        footer = self.env['ir.actions.report']._render_template('l10n_it_journal_custom.registri_iva_internal_layout', values=rcontext)
        footer = self.env['ir.actions.report']._render_template('web.minimal_layout', values=dict(rcontext, subst=True, body=Markup(footer.decode())))
        
        # ✅ DOCUMENT DATA - usa metodo padrão ma rimuove global_tax_summary
        document_data = self._generate_document_data_for_export(report, print_options, 'pdf')
        
        # global_tax_summary già rimosso in _generate_document_data_for_export quando è Fatture Acquisti EU
        # Ma verifichiamo comunque per sicurezza
        if document_data.get('global_tax_summary'):
            _logger.info("🎯 Rimozione global_tax_summary per Fatture Acquisti EU")
            document_data['global_tax_summary'] = False
        
        render_values = {
            'report': report,
            'options': print_options,
            'base_url': base_url,
            'document_data': document_data
        }
        
        # ✅ BODY PADRÃO ODOO (usa template standard)
        body = self.env['ir.qweb']._render(self._get_custom_display_config()['pdf_export']['pdf_export_main'], render_values)
        
        # ✅ GENERA PDF con footer customizzato (paginazione) ma senza header customizzato
        action_report = self.env['ir.actions.report']
        pdf_file_stream = io.BytesIO(action_report._run_wkhtmltopdf(
            [body],
            footer=footer.decode(),  # Footer customizzato (paginazione)
            landscape=False,
            specific_paperformat_args={
                'data-report-margin-top': 10,
                'data-report-header-spacing': 10,
                'data-report-margin-bottom': 15,
            }
        ))
        
        pdf_result = pdf_file_stream.getvalue()
        pdf_file_stream.close()
        
        _logger.info("🎯 PDF Fatture Acquisti EU generato con successo")
        
        return {
            'file_name': report.get_default_report_filename(options, 'pdf'),
            'file_content': pdf_result,
            'file_type': 'pdf',
        }

    def export_to_pdf(self, options):
        """
        Sovrascrive il metodo export_to_pdf per applicare personalizzazioni del modulo
        per TUTTI i registri del Journal Report (sia Registri IVA che Fatture Fornitore)
        ECCEZIONE: "Fatture Acquisti EU" usa layout PADRÃO + paginazione customizzata
        """
        try:
            report = self.env['account.report'].browse(options['report_id'])
            
            # Verifica se è specificamente il report "Journal Report" (che include sia Registri IVA che Fatture Fornitore)
            journal_report = self.env.ref('account_reports.journal_report', raise_if_not_found=False)
            if not journal_report or report.id != journal_report.id:
                # Se non è il Journal Report, utilizza comportamento standard
                return super().export_to_pdf(options)
            
            # ✅ CASO ESPECIAL: "Fatture Acquisti EU" - Layout PADRÃO + Paginazione CUSTOMIZZATA
            if self._is_fatture_acquisti_eu_only(options):
                _logger.info("🎯 Fatture Acquisti EU: layout PADRÃO + paginazione customizzata")
                return self._export_to_pdf_fatture_acquisti_eu(options, report)
            
            # ✅ APPLICA PERSONALIZZAZIONI PER TUTTI GLI ALTRI REGISTRI DEL JOURNAL REPORT
            _logger.info("Applicazione personalizzazioni del modulo per Journal Report")
            
            base_url = report.get_base_url()
            print_options = {
                **report.get_options(previous_options={**options, 'export_mode': 'print'}),
                'css_custom_class': self._get_custom_display_config().get('pdf_css_custom_class', 'journal_report_pdf')
            }
            rcontext = {
                'mode': 'print',
                'base_url': base_url,
                'company': self.env.company,
                'options': print_options,
                'report': report,
                'format_date_dd_mm_yyyy': self._format_date_for_template,
            }

            # Renderizza il footer utilizzando il nostro template specifico
            footer = self.env['ir.actions.report']._render_template('l10n_it_journal_custom.registri_iva_internal_layout', values=rcontext)
            footer = self.env['ir.actions.report']._render_template('web.minimal_layout', values=dict(rcontext, subst=True, body=Markup(footer.decode())))

            # Renderizza l'header personalizzato per TUTTI i registri
            header = self.env['ir.actions.report']._render_template('l10n_it_journal_custom.custom_header_layout', values=rcontext)
            header = self.env['ir.actions.report']._render_template('web.minimal_layout', values=dict(rcontext, subst=True, body=Markup(header.decode())))

            # Renderizza il corpo utilizzando il template personalizzato (senza header standard)
            document_data = self._generate_document_data_for_export(report, print_options, 'pdf')
            
            # ✅ RIMUOVI "RIEPILOGO GENERALE IMPOSTE" dai dati del documento
            if 'global_tax_summary' in document_data:
                _logger.info("Rimozione sezione 'Riepilogo Generale Imposte' dai dati del documento")
                del document_data['global_tax_summary']
            
            render_values = {
                'report': report,
                'options': print_options,
                'base_url': base_url,
                'document_data': document_data
            }
            body = self.env['ir.qweb']._render('l10n_it_journal_custom.registri_iva_body_without_header', render_values)

            # Genera il PDF con header e footer personalizzati
            action_report = self.env['ir.actions.report']
            pdf_file_stream = io.BytesIO(action_report._run_wkhtmltopdf(
                [body],
                header=header.decode(),  # Header personalizzato per TUTTI
                footer=footer.decode(),  # Footer personalizzato per TUTTI
                landscape=False,
                specific_paperformat_args={
                    'data-report-margin-top': 35,
                    'data-report-header-spacing': 40,
                    'data-report-margin-bottom': 15,
                }
            ))

            pdf_result = pdf_file_stream.getvalue()
            pdf_file_stream.close()

            return {
                'file_name': report.get_default_report_filename(options, 'pdf'),
                'file_content': pdf_result,
                'file_type': 'pdf',
            }
            
        except Exception as e:
            _logger.error(f"Errore in export_to_pdf personalizzato: {e}, utilizzo comportamento standard")
            return super().export_to_pdf(options) 