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

---

## Dipendenze

- `product`
- `product_expiry`

## Autore

**Bagubits SRLS**  
Website: https://bagubits.it

## Licenza

LGPL-3

