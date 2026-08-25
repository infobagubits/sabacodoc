# Sabaco - Fix numerazione sequenza (progressivo/N)

## Cosa risolve
Falso errore di validazione alla conferma di fatture/registrazioni con formato
a solo progressivo, es. `10/N`:

> La Data (08/04/2026) che hai aggiunto non è allineata con la sequenza
> numerica esistente (10/N).

Il problema si manifesta con la firma tipica:
- `1/N` … `9/N` → si confermano (1 cifra);
- `10/N` … `99/N` → errore (2 cifre lette come anno);
- `100/N` in poi → si confermano (3+ cifre).

## Come lo risolve
Override di `_deduce_sequence_number_reset` su `account.move`: se il nome della
sequenza contiene un solo blocco di cifre, il reset viene forzato a `never`
(numerazione continua, mai azzerata). In quel caso non può esistere una
componente anno/mese separata dal progressivo, quindi il controllo cronologico
data↔numero non viene più applicato in modo errato.

Le sequenze con anno esplicito (es. `2026/0001`, due blocchi di cifre) non
vengono toccate: seguono il comportamento standard di Odoo.

## Ambito
Il fix agisce su tutti i registri contabili (`account.move`): fatture clienti,
note di credito, fatture fornitori, registrazioni varie. Poiché è basato sulla
forma del numero e non sul singolo giornale, copre automaticamente anche gli
altri registri che usano lo stesso tipo di numerazione a solo progressivo.

## Installazione su odoo.sh
1. Aggiungi la cartella `sabaco_sequence_fix/` al repository del progetto
   (di norma sotto la directory dei moduli, es. `/` o `addons/`).
2. Fai commit e push su un **branch di staging**.
3. odoo.sh ricostruisce l'ambiente: aggiorna la lista app e installa il modulo
   ("Sabaco - Fix numerazione sequenza (progressivo/N)"), oppure forza
   l'aggiornamento con `-u sabaco_sequence_fix`.
4. Riproduci il caso `10/N` in staging e verifica che la conferma vada a buon
   fine. Solo dopo l'ok, fai merge sul branch di produzione.

## Avvertenze importanti
- **Testa prima in staging.** Non installare direttamente in produzione.
- Verifica, sulla tua versione installata di Odoo 18, che il metodo
  `_deduce_sequence_number_reset(self, name)` esista con questa firma nel
  mixin delle sequenze. È stabile da diverse versioni, ma la conferma va fatta
  sul codice effettivamente in esecuzione sulla tua istanza.
- Le fatture già registrate (es. `1/N`…`9/N`) non vengono modificate: il fix
  agisce sulla logica di validazione/deduzione, non riscrive i numeri esistenti.
- Se alcune fatture sono già state trasmesse a SdI, la numerazione trasmessa è
  immutabile per legge: questo modulo non la altera.

## Disinstallazione
Rimuovi il modulo dall'elenco app oppure elimina la cartella dal repository e
ricostruisci l'ambiente. Nessun dato viene creato o cancellato dal modulo.
