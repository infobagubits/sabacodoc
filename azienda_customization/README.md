# Azienda Customization

Modulo di customizzazioni generiche per il cliente **Sabaco**.

## Scopo del Modulo

Questo modulo centralizza tutte le modifiche e personalizzazioni generiche richieste da Sabaco che non rientrano in moduli specifici già esistenti.

---

## Customizzazioni Implementate

### 1. **Modifica testo campo data di scadenza prodotto** *(03/10/2025)*

**Modello:** `product.template`  
**Campo:** `expiration_time`  
**File:** `views/product_template_views.xml`

**Modifica:**
- **Prima:** "giorni che seguono la ricezione"
- **Dopo:** "giorni che seguono la produzione"

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

