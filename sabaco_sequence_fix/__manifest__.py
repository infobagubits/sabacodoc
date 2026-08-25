# -*- coding: utf-8 -*-
{
    "name": "Sabaco - Fix numerazione sequenza (progressivo/N)",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Evita il falso errore 'La data non è allineata con la sequenza' "
               "per numerazioni a solo progressivo (es. 10/N).",
    "description": """
Fix numerazione fatture con formato a solo progressivo (es. progressivo/N)
==========================================================================

Con un numero come ``10/N`` (progressivo a 2 cifre, nessun anno esplicito nel
formato) il motore delle sequenze di Odoo può interpretare il progressivo a due
cifre come se fosse un anno a 2 cifre. Di conseguenza il controllo cronologico
solleva un ``ValidationError`` del tipo:

    "La Data (08/04/2026) che hai aggiunto non è allineata con la sequenza
     numerica esistente (10/N)."

anche quando numero e data sono perfettamente crescenti. Sintomo tipico:
- 1/N ... 9/N  -> si confermano  (1 cifra: non sembra un anno)
- 10/N ... 99/N -> errore        (2 cifre: lette come anno)
- 100/N in poi -> si confermano  (3+ cifre: tornano numero)

Questo modulo forza il tipo di reset a 'never' (numerazione continua, mai
azzerata) per tutte le sequenze che contengono un solo blocco di cifre, come
``10/N``. In tali sequenze non può esistere una componente anno/mese distinta
dal contatore, quindi 'never' è l'unico esito corretto e il controllo
data/sequenza non viene più applicato erroneamente.

Non modifica le sequenze con anno esplicito (es. 2026/0001), che restano
invariate.
""",
    "author": "Sabaco d'oc Srl",
    "website": "",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
