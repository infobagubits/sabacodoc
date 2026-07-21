# Reverse Charge – Autofattura separata (IT) – Odoo 18

Al momento della registrazione (**post**) di una fattura fornitore soggetta a
reverse charge, il modulo:

1. registra la fattura fornitore (registro acquisti) – comportamento standard;
2. genera automaticamente una seconda `account.move` (**autofattura**, tipo
   `out_invoice`/`out_refund`) nel **sezionale vendite dedicato**;
3. assegna la **numerazione dedicata** del sezionale;
4. **collega** i due documenti (campi + smart button in entrambe le direzioni).

Rispetto allo standard Odoo (registrazione unica con imposta a doppia
ripartizione +100%/-100%), qui ottieni la **doppia registrazione** classica:
IVA a credito nel registro acquisti, IVA a debito nel registro vendite.

## Logica contabile (metodo del conto transitorio)

Dati imponibile `B` e IVA `V`:

**Fattura fornitore** (registro acquisti) – tramite l'imposta di *acquisto* RC:
```
Dare  Costo                 B
Dare  IVA a credito         V
Avere Debito v/fornitore    B      (il fornitore non addebita IVA)
Avere Conto transitorio RC  V      (ripartizione -100% dell'imposta acquisto)
```

**Autofattura** (registro vendite) – generata dal modulo con l'imposta di *vendita* mappata:
```
Dare  Conto contropartita (Credito)   B+V   (riga termini di pagamento)
Avere Conto transitorio imponibile    B      (riga imponibile)
Avere IVA a debito                    V
```

Vincolo Odoo: su un documento di vendita la riga dei termini di pagamento
deve stare su un conto di tipo **Credito**, mentre la riga imponibile **non**
deve esserlo. Per questo servono due conti distinti. Il conto contropartita e
il conto transitorio imponibile vengono azzerati/riconciliati dal
commercialista contro la contropartita della fattura di acquisto; l'IVA a
credito e l'IVA a debito si compensano in liquidazione ma compaiono in
entrambi i registri.

## Configurazione (obbligatoria)

Il modulo automatizza generazione e collegamento; l'impianto fiscale va
configurato una volta sola dal commercialista.

1. **Sezionale autofatture** – crea un giornale di tipo *Vendite* (es. "Registro
   Autofatture") con la sua numerazione.
2. **Conti**:
   - *Conto transitorio imponibile* – un conto NON di tipo Credito/Debito
     (es. tipo "Attività correnti" o transitorio), usato sulla riga imponibile
     dell'autofattura al posto di un ricavo reale;
   - *Conto contropartita (Credito)* – un conto di tipo **Credito**
     (`asset_receivable`), usato sulla riga di chiusura dell'autofattura.
3. **Imposte**:
   - imposta di **acquisto** RC (es. 22% RC acquisti) con ripartizione imposta
     `+100%` → *IVA a credito* e `-100%` → *conto transitorio RC*, con le
     opportune griglie fiscali (VJ / detraibile);
   - imposta di **vendita** per l'autofattura (es. 22% autofattura) con `+100%`
     → *IVA a debito* e le relative griglie;
   - sull'imposta di **acquisto**, valorizza il campo *"Imposta autofattura
     (reverse charge)"* puntando all'imposta di vendita.
4. **Posizione fiscale** – per ogni casistica (interno, intra-UE, extra-UE)
   crea/usa una posizione fiscale, spunta *"Reverse charge (autofattura
   separata)"* e imposta sezionale + i due conti. In alternativa i default
   aziendali sono su `res.company` (campi `l10n_it_rc_*`).
   - *"Applica reverse charge di default"*: se attivo, il flag reverse charge
     sulle fatture fornitore è preselezionato; se disattivo, la posizione è
     abilitata ma l'operatore attiva il flag manualmente quando serve.

## Trasmissione allo SdI (TD16/17/18/19)

Il TipoDocumento si imposta sul campo standard **"Document Type"
(`l10n_it_document_type`)**, fornito dal modulo `l10n_it_edi_ndd`
(auto-installato con `l10n_it_edi`). Sull'autofattura scegli manualmente
TD16/17/18/19: quando è uno di questi, il modulo la marca come self-invoice e
l'XML FatturaPA inverte automaticamente le parti — **CedentePrestatore =
fornitore**, **CessionarioCommittente = la tua azienda**, regime `RF18`.

Alla generazione l'autofattura viene creata con il TipoDocumento **azzerato**:
va scelto dall'operatore prima dell'invio.

Quale TD: **TD16** interno (art. 17 c. 6), **TD17** servizi da estero,
**TD18** beni intra-UE, **TD19** beni ex art. 17 c. 2 (già in Italia).
Perché l'XML riporti aliquota e imposta, l'imposta di vendita mappata deve
avere l'aliquota reale (es. 22% → IVA a debito).

Se nel menu a tendina di "Document Type" **non compaiono** TD16-19: i record
sono standard (`l10n_it_edi_ndd`), quindi (a) aggiorna quel modulo perché il
CSV venga ricaricato, e/o (b) questo modulo neutralizza un eventuale dominio
sul campo (vista a priorità 100) così che tutti i TipoDocumento siano
selezionabili.

### Griglie IVA (VJ) gestite dal modulo

Alla scelta/modifica del TipoDocumento, il modulo assegna in **autonomia** il
tag della griglia VJ dell'imponibile sull'autofattura, col segno che rende
positivo l'importo in dichiarazione: **TD17→VJ3**, **TD18→VJ9**, **TD19→VJ3**.
Per **TD16** la griglia dipende dall'operazione (VJ6/7/8/12–17) e non viene
assegnata in automatico.

Per non duplicare, l'imposta di **acquisto** sulla fattura fornitore deve
portare solo la parte **detraibile** (IVA a credito) e **non** i tag VJ.

> Verifica sempre segno e importi della **liquidazione IVA** sui primi
> documenti reali.

## Uso

Registra la fattura fornitore con la posizione fiscale RC (il flag *Reverse
charge* si precompila, resta modificabile). Al **post**, l'autofattura viene
creata e registrata nel sezionale; usa gli smart button per navigare fra i due
documenti.

## Avvertenze importanti

- **Validazione contabile**: verifica con il tuo commercialista scritture,
  griglie IVA e liquidazione sulla tua reale contabilità/piano dei conti prima
  di usare in produzione. Il modulo non impone codici conto specifici.
- **Fatturazione elettronica (SdI / `l10n_it_edi`)**: il modulo trasmette
  l'autofattura come TD16/17/18/19 invertendo le parti nell'XML (vedi sopra).
  Verifica sempre l'anteprima XML e l'esito SdI sui primi documenti reali, e
  controlla che le griglie VJ non risultino duplicate in liquidazione.
- **Riferimento**: l'associazione OCA mantiene il modulo
  `l10n_it_reverse_charge`, implementazione collaudata dello stesso schema
  (con tipi RC, chiusure transitorie, ecc.). Utile come confronto/alternativa.

## Compatibilità

Odoo 18 (Community/Enterprise). Dipendenze: `account`, `l10n_it`.
Licenza: LGPL-3.
