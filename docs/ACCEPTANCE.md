# Matrice di accettazione D1

Aggiornamento 27 settembre 2026: fondamenta **T01 verificate**, con limiti espliciti nelle righe condivise con milestone future. Evidenze nel [report T01](reports/T01.md), codice `26986e7`. Gli altri requisiti D1 restano non verificati.

Le prove di dettaglio sono nelle schede task e in riferimento §14. La matrice non può ridurre il perimetro di riferimento §2.3.

| ID | Requisito | Task | Evidenza richiesta | Stato iniziale |
|---|---|---|---|---|
| A01 | Una economia, Governo/BC/valuta unici; popolazione e banche configurabili | T01 | `test_config.py`, `test_initialization.py`; [report](reports/T01.md) | Verificato T01 |
| A02 | Ledger a contropartite, bilanci di apertura e registri proprietari coerenti | T01 | `test_opening_accounts_and_ownership`, costi fisici e diagnostica CLI; [report](reports/T01.md) | Verificato T01 |
| A03 | Credito/depositi/riserve distinti, settlement atomico | T01/T03 | `test_accounting.py`: 100/40, riserve, errori e consegna; [report](reports/T01.md) | Primitive T01 verificate; facilities/decisione creditizia T03 non verificate |
| A04 | Bisogni primari/secondari/lusso e budget finiti | T02 | Priorità, limite fisico e vincolo di spesa | Non verificato |
| A05 | Lavoro, salari emergenti, occupazione unica | T02 | Matching e paga settimanale reale | Non verificato |
| A06 | Produzione vincolata da input, capitale e lavoro; giacimenti | T02 | Bilanci fisici e casi senza input/lavoro | Non verificato |
| A07 | Mercati distinti e prezzi transati, offerti e domanda non evasa | T02 | Matching, scorte, mancati scambi e tabelle mercato | Non verificato |
| A08 | Credito rolling e vincoli finanziari | T03 | Tassi, revisione, rifiuti, erogazioni uniche | Non verificato |
| A09 | Strumenti BC, interessi e facilities con collateral | T03 | Trasmissione tassi e garanzie non duplicate | Non verificato |
| A10 | Tasse, conto Tesoro, acquisti pubblici | T04 | Ciclo cassa con contropartite | Non verificato |
| A11 | Asta bond e acquisti BC effettivi | T04 | Prezzo marginale, pareggi, budget e invenduto | Non verificato |
| A12 | Scadenza pubblica, costo ammortizzato e deficit non finanziato | T04 | Rimborso dopo 52 settimane e default controllato | Non verificato |
| A13 | Quote societarie, diluizione e dividendi | T05 | Registri e asta fallita/riuscita | Non verificato |
| A14 | Investimento reale e capacità da t+1 | T02/T05 | Finanziamento, acquisto e installazione | Non verificato |
| A15 | Default imprese, liquidazioni e perdite | T05 | Recuperi solo realizzati e priorità creditori | Non verificato |
| A16 | Risoluzione bancaria e distinzione liquidità/solvibilità | T05 | Caso numerico, perdite soci/depositanti e riserve | Non verificato |
| A17 | Pausa, +1, +N, automatico e velocità | T06/T07 | Manuale/batch/automatico e pausa in corso | Non verificato |
| A18 | Comandi idempotenti e politiche a confine di step | T06 | Duplicati, concorrenza e settimana assegnata | Non verificato |
| A19 | Step atomico, errori e terminazioni distinti | T06 | Errore iniettato e default economico | Non verificato |
| A20 | Checkpoint/ripresa deterministica | T06 | 100 vs 40+60 e checksum | Non verificato |
| A21 | API, snapshot e riconnessione | T06/T07 | Eventi persi, recupero e due schede | Non verificato |
| A22 | Dashboard, pannello BC, mercati e agenti su dati reali | T07 | Percorso browser e ispezione UI | Non verificato |
| A23 | Salvataggi ed export di tutte le settimane | T06/T07 | CSV completo e import in pausa | Non verificato |
| A24 | Metriche definite: CPI/PIL, lavoro, credito, distribuzione | T08 | Dizionario e riconciliazioni | Non verificato |
| A25 | Scenari e almeno cinque seed nei principali | T08 | Report riproducibile, inclusi collassi | Non verificato |
| A26 | Baseline 260 settimane, prestazioni misurate | T08 | Tempi, p95, memoria, macchina/versioni | Non verificato |
| A27 | Installazione locale e build servita da backend | T09 | Installazione pulita e smoke test | Non verificato |
| A28 | Target Windows e istruzioni macOS/Linux | T09 | Piattaforme testate e limiti dichiarati | Non verificato |
| A29 | Niente feature D2/D3 fittiziamente funzionanti | T07/T09 | Audit UI, scope e README | Non verificato |

## Regole per l'evidenza

- Un nome di test non prova il superamento: riportare comando eseguito, risultato e versione del codice.
- Se un ambiente non permette una prova, indicare NON ESEGUITO e motivare; non segnarla verificata.
- I report possono essere creati in `docs/reports/` durante lo sviluppo. Non creare adesso risultati vuoti che sembrino report eseguiti.
- Una revisione documentale prova coerenza delle istruzioni, non funzionamento o plausibilità empirica del simulatore.
- Quando cambia una feature già verificata, rivalutare le prove interessate; non ripetere indiscriminatamente l'intera suite se non risolve un rischio concreto.

## Accettazione finale

T09 può dichiarare D1 completo soltanto quando le righe pertinenti sono verificate e i criteri riferimento §14.4 soddisfatti. Se il lavoro è pronto ma manca un gate ambientale, consegnare il risultato descrivendo il gate ancora aperto senza falsificare lo stato.

## Requisiti prestazionali aggiunti nell'integrazione

| ID | Requisito | Task | Evidenza richiesta | Stato iniziale |
|---|---|---|---|---|
| A30 | Stato per colonne e layout compatibile NumPy | T01 | `test_column_mapping_isolation_and_no_duplicate_balances`; [contratti](technical/t01_contracts.md) | Verificato T01 |
| A31 | Kernel batch con riferimento scalare | T02/T08 | Stessi input/RNG, tolleranze e decisioni preservate | Non verificato |
| A32 | Precisione monetaria e buffer/rollback coerenti | T01/T06 | Budget esatti, contesto Decimal, copie isolate, staging transazioni; [report](reports/T01.md) | T01 verificato; rollback di step/storico/checkpoint T06 non verificati |
| A33 | Profiling e benchmark di scala | T08 | Costi per fase, kernel vs end-to-end, 10.000/52 e stima 100.000 | Non verificato |
