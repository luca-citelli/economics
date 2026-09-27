# Decisioni di progetto

Registro iniziale del 27 settembre 2026. «Baseline» indica una decisione incorporata nella specifica corrente, non un risultato empirico. Le nuove decisioni devono indicare motivazione, alternative, impatto, sezioni aggiornate e verifiche.

## Baseline

| ID | Decisione | Motivazione | Riferimento |
|---|---|---|---|
| D001 | Webapp locale, Python/FastAPI + React/TypeScript/Vite | Controlli interattivi e possibilità di hosting futuro senza riscrivere il motore | riferimento §3 |
| D002 | Un Governo, una BC, una valuta, economia chiusa | Perimetro iniziale richiesto; nessun settore estero implicito | §2 |
| D003 | Giocatore = BC; Governo autonomo | Separare strumenti monetari da fiscalità e shock sperimentali | §4, §9 |
| D004 | Settimana discreta, runner indipendente dal tempo economico | Riproducibilità fra step, batch e automatico | §5 |
| D005 | Mercati espliciti con razionamento e prezzi osservabili | I prezzi devono emergere dagli scambi | §8 |
| D006 | Moneta bancaria, riserve e Tesoro separati, ledger unico autorevole | Evitare doppio conteggio e trasferimenti senza contropartita | §6 |
| D007 | Popolazione adulta fissa nel D1 | Rinviare nuclei familiari, mortalità e successioni senza eliminarli dalla roadmap | §2.4, §7.4 |
| D008 | Bond zero coupon 52 settimane, asta uniforme, nessun secondario D1 | Prezzo/rendimento endogeni con contratti gestibili | §8.6 |
| D009 | Quote primarie di imprese esistenti e bene capitale fisico | Collegare raccolta finanziaria e aumento reale di capacità | §8.7, §7.3 |
| D010 | Acquisti BC primari stilizzati e facilities garantite | Prima implementazione esplicita; non presentarla come QE BCE | §9.2 |
| D011 | Conversione depositi in quote nella risoluzione D1, ricapitalizzazione pubblica D2 | Distinguere perdite, capitale e liquidità | §9.3 |
| D012 | Prezzi offerti, matching sequenziale randomizzato riproducibile | Mercati semplici ma completi senza order book universale | §8.3 |
| D013 | Conti Decimal, quantità float64; checkpoint JSON versionato | Precisione contabile e portabilità | §5.5, §6.1 |
| D014 | Nove milestone, lettura mirata, file comuni brevi | Ridurre contesto ripetuto mantenendo una fonte completa | docs/INDEX.md; docs/READING_GUIDE.md |
| D015 | Dati macro derivati, nessuna previsione economica garantita | Separare validità software e validazione del modello | §1, §11, §14 |

## Dettagli da definire nell'implementazione

Questi punti sono intenzionalmente assegnati a task; non sono segnaposto di documentazione dimenticati. Il proprietario non deve rispondere preventivamente a ogni parametro numerico. Lo sviluppatore adotta una scelta coerente, la documenta e la sottopone a verifica.

| ID | Dettaglio | Responsabile | Criterio |
|---|---|---|---|
| I001 | Versioni Python/Node e dipendenze precise | T01, T07 | Compatibilità Windows e lockfile riproducibile; nessuna versione inventata come installata |
| I002 | Ricette, unità dei prodotti, produttività, salari iniziali e deperimenti | T01; calibrazione T08 | Filiera avviabile, nessun ciclo senza input, valori con unità |
| I003 | Dotazioni e contropartite di apertura, proprietà iniziali | T01 | Bilanci riconciliati, quote non orfane; nessuna moneta gratuita durante gli step |
| I004 | Coefficienti comportamentali e limiti del credito | T01/T03; calibrazione T08 | Default documentati, regole interpretabili e test su estremi |
| I005 | Importi fiscali e cassa/nominale iniziali del Tesoro | T01/T04; calibrazione T08 | Scala coerente con popolazione, maturità e risorse |
| I006 | Trattamento completo di inventari e contabilità statistica del PIL | T02/T08 | Riconciliazione senza voce residua artificiale |
| I007 | Dettagli JSON di snapshot/comandi/checkpoint | T01 per contratto minimo, T06 per schema eseguibile | Tipizzazione, versioni, idempotenza, round trip |
| I008 | Limiti/haircut garanzie, grace period, liquidazioni e capitale target | T03/T05 | Risoluzione esplicita, niente recuperi impliciti |
| I009 | Macchina di riferimento e obiettivo prestazionale misurato | T08 | Report riproducibile; velocità richiesta diversa da effettiva |

## Come registrare una nuova decisione

Usare il prossimo ID D disponibile e indicare: data/task; problema; decisione; motivazione; effetti su API/contabilità/UI; sezioni e test interessati. Se cambia una regola già fissata nei moduli correnti, aggiornare il modulo normativo e le relative schede e registrare l'accordo sul cambiamento. Una nota in questo file non prevale da sola su una regola contraria.

Non esistono ancora decisioni derivate da implementazione, benchmark o test del modello.

## Integrazione documentale 3.2

- D016 — Fonte unica per argomento: i moduli in docs/model e docs/technical contengono le regole; SPEC è una panoramica e INDEX la mappa. Le schede task richiamano i moduli. Motivazione: lettura selettiva senza doppia manutenzione.
- D017 — Conservazione dei contenuti: le regole economiche 3.1 restano la baseline; v2 conservata solo come archivio storico. Il ciclo vecchio e i regimi monetari immediati della v2 non sostituiscono quelli aggiornati.
- D018 — Nessun gate decisionale nuovo per iniziare T01. I tre orientamenti di prodotto più rilevanti hanno default espliciti in docs/PRODUCT_DECISIONS.md; un cambio sostanziale richiede aggiornamento dei moduli e dei task interessati.

Le scelte residue I001–I009 sono dettagli tecnici/calibrazioni assegnati agli sviluppatori; non richiedono nove domande preventive al proprietario.

## Requisito aggiunto durante l'integrazione

- D019 — Richiesta esplicita del proprietario: predisporre il simulatore al calcolo vettoriale NumPy e all'efficienza. Adottato dal T01 layout per colonne e kernel separati; implementazione ibrida progressiva, non riscrittura futura obbligata. Specifica in docs/technical/performance_and_vectorization.md.
- D020 — Il ledger D1 rimane Decimal; NumPy tratta calcoli numerici e proiezioni non autorevoli. Un futuro ledger a interi scalati è una migrazione tecnica da misurare/validare separatamente, non una scelta imposta ora al proprietario.

I010 — T01 documenta layout/dtype/RNG e confine monetario; T02 implementa i primi kernel; T06 atomicità efficiente; T08 profila e misura la scala. Nessuna decisione bloccante del proprietario su dettagli NumPy.
