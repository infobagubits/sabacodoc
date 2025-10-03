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

**Dettaglio tecnico:** Viene sostituito il `<span>` che contiene il testo informativo accanto al campo `expiration_time` nella view `product_expiry.view_product_form_expiry`.

**Motivazione:** Il cliente Sabaco necessita che il testo faccia riferimento alla produzione invece del ricevimento per allinearsi con i loro processi interni.

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

**Motivazione:** Campi non necessari per i processi aziendali di Sabaco e richiedono una interfaccia più pulita e semplificata.

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

