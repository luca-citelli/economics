# Strumenti della banca centrale

Documento normativo corrente (revisione 3.2). Riferimenti storici: §9.2. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 9.2 Strumenti monetari D1

| Strumento utente | Effetto economico | Vincoli |
|---|---|---|
| Tasso sulle riserve `reserve_rate` | Remunerazione delle riserve bancarie; riferimento per opportunità e tassi sui depositi | Annuale; applicato allo stock iniziale della settimana |
| Tasso di rifinanziamento `policy_rate` | Prezzo del credito ordinario BC alle banche; riferimento delle offerte di credito | `reserve_rate ≤ policy_rate` |
| Tasso d'emergenza `emergency_rate` | Prezzo di liquidità eccezionale | `policy_rate ≤ emergency_rate` |
| Accesso/limiti al rifinanziamento | Quantità di credito BC disponibile per banche ammissibili | Garanzie idonee, haircut, cap per banca |
| Liquidità d'emergenza abilitata | Prestiti ulteriori a banche solventi secondo criteri più ampi | Non ricapitalizza banche insolventi |
| Acquisti di bond primari | Ordine d'acquisto della BC all'asta | Budget, prezzo massimo e offerta disponibile |

Usare un unico significato del `policy_rate`: qui è il tasso della facility ordinaria, non un quarto tasso astratto scollegato dai contratti. I limiti prudenziali delle banche sono parametri di scenario; non diventano automaticamente strumenti del giocatore.

La facility ordinaria accetta nel D1 titoli pubblici non già vincolati. L'emergenza può accettare anche prestiti performing con haircut configurato. I prestiti BC durano una settimana, sono rinnovabili se ammissibili; a inizio step interessi e rientri vengono verificati. Il collateral rimane nel bilancio della banca ed è segnato come vincolato.

Interessi sulle riserve creano/assorbono riserve con contropartita nel risultato della BC. Il patrimonio della BC può diventare negativo senza automatica terminazione; la UI lo segnala. Non trasferire automaticamente utili BC al Governo nel D1.
