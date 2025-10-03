# Azienda Customization

Modulo di customizzazioni generiche per il cliente **Sabaco**.

## Scopo del Modulo

Questo modulo centralizza tutte le modifiche e personalizzazioni generiche richieste da Sabaco che non rientrano in moduli specifici già esistenti.

---

## Customizzazioni Implementate

### 1. **Modifica testo informativo campo data di scadenza prodotto** *(03/10/2025)*

**Modello:** `product.template`  
**Campo:** `expiration_time`  
**File:** `views/product_template_views.xml`

**Modifica:**
- **Prima:** "days after receipt" (tradotto come "giorni che seguono la ricezione")
- **Dopo:** "giorni che seguono la produzione"

**Dettaglio tecnico:** Viene sostituito l'intero `<div>` che contiene il campo `expiration_time` e il relativo `<span>` informativo nella view `product_expiry.view_product_form_expiry`, utilizzando un XPath che localizza il div successivo al label del campo e lo sostituisce con uno nuovo contenente il testo corretto.

**Motivazione:** Il cliente Sabaco necessita che il testo faccia riferimento alla produzione invece del ricevimento per allinearsi con i loro processi interni legati alla produzione anziché al ricevimento della merce.

### 2. **Nascondere campi nel form prodotto** *(03/10/2025)*

**Modello:** `product.template`  
**File:** `views/product_template_views.xml`

**Campi nascosti:**

1. **standard_price** (Costo)
   - **Posizione:** Tab Generale
   - **Azione:** Nascosto label + div intero
   
2. **sale_delay** (Tempo di risposta al cliente)
   - **Posizione:** Tab Magazzino
   - **Azione:** Nascosto label + div intero
   
3. **removal_time** (Data di rimozione)
   - **Posizione:** Tab Magazzino (sezione Date)
   - **Azione:** Nascosto label + div intero

**Dettaglio tecnico:** Per ogni campo nascosto, vengono creati XPath specifici che ereditano dalle view originali (`product.product_template_form_view`, `stock.view_template_property_form`, e `product_expiry.view_product_form_expiry`) e applicano l'attributo `invisible="1"` sia al `<label>` che al `<div>` contenente il campo, garantendo che l'intera riga sia completamente nascosta dall'interfaccia utente.

**Motivazione:** Campi non necessari per i processi aziendali di Sabaco. Il cliente richiede una interfaccia più pulita e semplificata, focalizzata solo sui dati essenziali per le loro operazioni quotidiane.

### 3. **Rinominare opzione "Consumabile" in "Prodotto" nel campo Product Type** *(03/10/2025)*

**Modello:** `product.template`  
**Campo:** `type`  
**File:** `models/product_template.py`

**Modifica:**
- **Prima:** "Consumabile" (valore: `consu`)
- **Dopo:** "Prodotto" (valore: `consu`)

**Dettaglio tecnico:** Viene ereditato il modello `product.template` e sovrascritto il campo `type` (Selection) mantenendo gli stessi valori (`consu`, `service`, `combo`) ma modificando la label della prima opzione da "Consumabile" a "Prodotto", rendendo la terminologia più comprensibile per gli utenti finali.

**Motivazione:** Il termine "Consumabile" risulta poco chiaro per gli utenti. Il cliente preferisce utilizzare il termine più generico "Prodotto" che rappresenta meglio la natura degli articoli gestiti.

---

## Dipendenze

- `product`
- `product_expiry`
- `stock`

## Autore

**Bagubits SRLS**  
Website: https://bagubits.it

## Licenza

LGPL-3

