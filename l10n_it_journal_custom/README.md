# Personalizzazione Registri Contabili Italiani

🇮🇹 **Modulo professionale per la personalizzazione avanzata dei registri contabili italiani in Odoo 18**

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](https://github.com/bellomatheus/luglio)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL%203-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Odoo](https://img.shields.io/badge/Odoo-18.0-purple.svg)](https://www.odoo.com)

---

## 🎯 Panoramica

Questo modulo fornisce personalizzazioni avanzate specificamente progettate per i registri contabili italiani, offrendo layout professionali, calcoli automatici, **consolidamento automatico imposte duplicate** e numerazione personalizzata per **Registri IVA** e **Fatture Fornitore**.

## ⭐ Caratteristiche Principali

### 📊 **REGISTRI IVA**
- ✅ **Header dinamico personalizzato** su tutte le pagine
- ✅ **Rimozione automatica della data** dall'header standard
- ✅ **Numerazione pagine con offset** configurabile
- ✅ **Titolo dinamico** che riflette il nome del registro
- ✅ **Informazioni aziendali complete** (Partita IVA, Codice Fiscale)
- ✅ **Layout ottimizzato** per stampa professionale

### 📋 **TUTTI I REGISTRI**
- ✅ **Colonne ottimizzate** (rimuove "Conto" e "Griglie Imposta")
- ✅ **Totali automatici** nella sezione "Imposta Applicata"
- ✅ **Calcolo dinamico** di:
  - Importo Imponibile
  - Importo Imposta
  - Non Deducibile
  - Deducibile
  - In Scadenza
- ✅ **Rimozione automatica** sezione "Griglie Imposte Interessate"
- ✅ **Layout pulito e professionale** per tutti i tipi di registri
- ✅ **CONSOLIDAMENTO AUTOMATICO**: Impostos duplicados são agrupados e somados em uma única linha

## 🔧 Requisiti di Sistema

- **Odoo Community/Enterprise**: 18.0+
- **Moduli dipendenti**:
  - `base`
  - `account_reports`
  - `l10n_it` (Localizzazione italiana)

## 📦 Installazione

### Metodo 1: Git Clone
```bash
cd /percorso/del/tuo/odoo/addons
git clone https://github.com/bellomatheus/luglio.git
```

### Metodo 2: Download Diretto
1. Scarica il modulo dalla repository
2. Estrai nella cartella `addons` di Odoo
3. Riavvia il server Odoo
4. Aggiorna la lista dei moduli: **Apps → Aggiorna Lista App**
5. Cerca "Personalizzazione Registri Contabili Italiani"
6. Clicca **Installa**

## ⚙️ Configurazione

### Accesso Rapido
**Impostazioni → Contabilità → Report Italiani - Numerazione Pagine**

### Parametri Configurabili

| Parametro | Descrizione | Valori |
|-----------|-------------|---------|
| `l10n_it_custom.page_offset_enabled` | Abilita numerazione personalizzata | `True/False` |
| `l10n_it_custom.page_offset` | Numero pagina iniziale | Intero (es: 12) |

### Esempio di Configurazione
```xml
<!-- Inizia numerazione dalla pagina 12 -->
<record id="page_offset_enabled" model="ir.config_parameter">
    <field name="key">l10n_it_custom.page_offset_enabled</field>
    <field name="value">True</field>
</record>

<record id="page_offset_value" model="ir.config_parameter">
    <field name="key">l10n_it_custom.page_offset</field>
    <field name="value">12</field>
</record>
```

## 🚀 Utilizzo

### Registri IVA
1. Vai a **Contabilità → Registri Contabili**
2. Seleziona periodo e filtri desiderati
3. Genera PDF → Vedrai header personalizzato e numerazione con offset

### Fatture Fornitore
1. Vai a **Contabilità → Registri Contabili**
2. Seleziona solo registri di tipo "Acquisto"
3. Genera PDF → Colonne ottimizzate + totali automatici

## 🎨 Comportamento Intelligente

| Tipo Report | Header | Colonne | Totali | Tax Grids |
|-------------|--------|---------|--------|-----------|
| **Registri IVA** | ✅ Personalizzato | ✅ Standard | ❌ | ✅ Visibili |
| **Fatture Fornitore** | ✅ Personalizzato | ✅ Filtrate | ✅ Automatici | ❌ Nascoste |
| **Altri Report** | ❌ Standard | ✅ Standard | ❌ | ✅ Standard |

## 🐛 Risoluzione Problemi

### Numerazione non funziona
```bash
# Verifica parametri
SELECT key, value FROM ir_config_parameter 
WHERE key LIKE 'l10n_it_custom%';
```

### Header non visualizzato
- Assicurati di stare generando un **PDF**
- Verifica che sia selezionato il report **"Registri Contabili"**

### Totali errati in Fatture Fornitore
- Controlla i log di Odoo per messaggi di debug
- Verifica che i registri selezionati siano di tipo "Acquisto"

## 📝 Log e Debug

Il modulo include logging dettagliato:

```python
_logger.info("Applicazione personalizzazioni del modulo per Journal Report")
_logger.info("Totali formattati per Fatture Fornitore: {totals}")
```

Per abilitare debug: **Impostazioni → Parametri Tecnici → Logging**

## 🤝 Supporto

### Sviluppato da
**Bagubits SRLS**
- 🌐 **Website**: [https://bagubits.it](https://bagubits.it)
- 📧 **Email**: info@bagubits.it
- 📞 **Telefono**: +39 XXX XXX XXXX

### Contributori
- Matheus Bello (@bellomatheus)

## 📄 Licenza

Questo modulo è rilasciato sotto licenza [LGPL-3](https://www.gnu.org/licenses/lgpl-3.0.html).

## 🔄 Changelog

### v1.3.0 (2025-01-XX)
- ✅ **CONSOLIDAMENTO AUTOMATICO**: Impostos duplicados agora são agrupados e somados automaticamente
- ✅ Novo método `_format_consolidated_tax_line` para linhas consolidadas
- ✅ Melhor performance ao processar relatórios com muitas linhas de imposto
- ✅ Logging detalhado do processo de consolidamento

### v1.2.0 (2024-12-XX)
- ✅ Traduzione completa in italiano
- ✅ Aggiornamento informazioni Bagubits SRLS
- ✅ Miglioramento documentazione
- ✅ Rimozione sezione "Griglie Imposte Interessate" per Fatture Fornitore

### v1.1.0 (2024-12-XX)
- ✅ Totali automatici per Fatture Fornitore
- ✅ Personalizzazione colonne
- ✅ Debug logging avanzato

### v1.0.0 (2024-12-XX)
- ✅ Rilascio iniziale
- ✅ Header personalizzato per Registri IVA
- ✅ Numerazione pagine con offset

---

## 🌟 Se questo modulo ti è utile, considera di lasciare una ⭐ su GitHub!

**Made with ❤️ in Italy by Bagubits SRLS** 