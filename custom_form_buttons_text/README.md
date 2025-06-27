# Testo Pulsanti Modulo Personalizzato

## Descrizione

Questo modulo aggiunge testo descrittivo ai pulsanti di azione standard di Odoo 18 che normalmente appaiono solo come icone, con bordi colorati per un maggiore risalto visivo.

## Funzionalità

### Pulsanti Modificati:

1. **Salva manualmente** - Pulsante di salvataggio manuale (icona nuvola) - Verde
2. **Scarta tutte le modifiche** - Pulsante per scartare le modifiche (icona X) - Rosso
3. **Azioni** - Pulsante azioni/menu (icona ingranaggio) - Grigio

### Caratteristiche:

- ✅ Il testo appare a destra delle icone esistenti
- ✅ Bordi colorati per una migliore identificazione visiva
- ✅ Effetti hover e animazioni fluide
- ✅ Responsivo - testo nascosto su schermi piccoli (mobile)
- ✅ Supporto per stati disabilitati
- ✅ Effetti di focus per l'accessibilità
- ✅ Non interferisce con le funzionalità esistenti
- ✅ Compatibile con Odoo 18
- ✅ Due implementazioni disponibili (CSS e JavaScript)

### Miglioramenti Visivi:

- **Bordi colorati**: Verde per Salva, Rosso per Scarta, Grigio per Azioni
- **Sfondi sottili**: Colori di sfondo complementari ai bordi
- **Effetti hover**: Cambio di colore e ombra al passaggio del mouse
- **Animazioni**: Transizioni fluide ed effetto clic
- **Accessibilità**: Outline di focus per la navigazione da tastiera

## Installazione

1. Copiare il modulo nella directory `customaddons/`
2. Aggiornare l'elenco dei moduli in Odoo
3. Installare il modulo "Testo Pulsanti Modulo Personalizzato"
4. I testi e i bordi appariranno automaticamente in tutte le viste modulo

## Implementazioni Disponibili

### 1. CSS (Predefinita - Consigliata)
- **File**: `static/src/scss/form_buttons_text.scss`
- **Vantaggi**: 
  - Più performante
  - Non interferisce con JavaScript
  - Caricamento più veloce
  - Effetti visivi nativi
- **Tecnologia**: Pseudo-elementi `::after` + SCSS

### 2. JavaScript (Alternativa)
- **File**: `static/src/js/form_buttons_text.js`
- **Vantaggi**:
  - Maggiore controllo sul DOM
  - Possibilità di logica condizionale
  - Più flessibile per personalizzazioni complesse
- **Tecnologia**: Patch del FormController

### Come Alternare Tra le Implementazioni

Nel file `__manifest__.py`, commentare/decommentare le righe:

```python
'assets': {
    'web.assets_backend': [
        # Soluzione CSS (predefinita)
        'custom_form_buttons_text/static/src/scss/form_buttons_text.scss',
        
        # Soluzione JavaScript (alternativa)
        # 'custom_form_buttons_text/static/src/js/form_buttons_text.js',
    ],
},
```

## Personalizzazione

### Per CSS:
Modificare `static/src/scss/form_buttons_text.scss`:

**Cambiare testo:**
```scss
.o_form_status_indicator_buttons .o_form_button_save::after {
    content: "Il tuo testo personalizzato";
}
```

**Cambiare colori dei bordi:**
```scss
.o_form_button_save {
    border-color: #tuo-colore !important;
    background-color: #tuo-colore-di-sfondo;
}
```

### Per JavaScript:
Modificare `static/src/js/form_buttons_text.js`:
```javascript
textSpan.textContent = 'Il tuo testo personalizzato';
```

## Responsività

Il modulo include media query che:
- Nascondono il testo su dispositivi mobili (larghezza < 768px)
- Mantengono i bordi e gli effetti visivi
- Regolano il padding per schermi più piccoli

## Compatibilità

- Odoo 18.0+
- Tutti i browser moderni
- Mobile e Desktop
- Funziona con temi personalizzati
- Supporto completo per l'accessibilità

## Struttura del Modulo

```
custom_form_buttons_text/
├── __init__.py
├── __manifest__.py
├── README.md
├── security/
│   └── ir.model.access.csv
└── static/
    └── src/
        ├── scss/
        │   └── form_buttons_text.scss
        └── js/
            └── form_buttons_text.js
```

## Supporto

Per domande o personalizzazioni aggiuntive, contattare il team di sviluppo. 