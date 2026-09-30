# Matrice di accettazione D1

Aggiornamento 30 settembre 2026: **T01–T07 verificati** nei rispettivi profili. Evidenze nei report [T01](reports/T01.md), [T02](reports/T02.md), [T03](reports/T03.md), [T04](reports/T04.md), [T05](reports/T05.md), [T06](reports/T06.md) e [T07](reports/T07.md). Le righe condivise distinguono il nucleo verificato dalle parti future; D1 resta incompleto.

Le prove di dettaglio sono nelle schede task e in riferimento §14. La matrice non può ridurre il perimetro di riferimento §2.3.

| ID | Requisito | Task | Evidenza richiesta | Stato corrente |
|---|---|---|---|---|
| A01 | Una economia, Governo/BC/valuta unici; popolazione e banche configurabili | T01 | `test_config.py`, `test_initialization.py`; [report](reports/T01.md) | Verificato T01 |
| A02 | Ledger a contropartite, bilanci di apertura e registri proprietari coerenti | T01 | `test_opening_accounts_and_ownership`, costi fisici e diagnostica CLI; [report](reports/T01.md) | Verificato T01 |
| A03 | Credito/depositi/riserve distinti, settlement atomico | T01/T03 | `test_accounting.py`, erogazione cross-bank e invariato stock aggregato di riserve; [report T03](reports/T03.md) | Verificato T01/T03 |
| A04 | Bisogni primari/secondari/lusso e budget finiti | T02 | `test_real_kernels.py`, priorità/limiti fisici in `test_real_simulation.py`; [report T02](reports/T02.md) | Verificato T02 |
| A05 | Lavoro, salari emergenti, occupazione unica | T02 | Matching a turni, salari unici, revisioni e settlement fallito in `test_real_simulation.py`; trattenuta T04 in `test_treasury.py` | Verificato T02/T04 |
| A06 | Produzione vincolata da input, capitale e lavoro; giacimenti | T02 | Quattro fattori mancanti, energia pregressa, costo medio e invarianti su 52 settimane; [report T02](reports/T02.md) | Verificato T02 |
| A07 | Mercati distinti e prezzi transati, offerti e domanda non evasa | T02 | `test_real_markets.py`, prezzi e CPI senza scambi; acquisti pubblici in `test_treasury.py` | Verificato T02/T04 |
| A08 | Credito rolling per imprese e fabbisogni primari delle persone; confronto di massimo K banche e vincoli finanziari | T03 | `test_household_primary_shortfall_requests_rolling_credit`, `test_credit_compares_other_banks_and_settles_reserves`, rifiuti/limiti in `test_finance.py`; [report T03](reports/T03.md) | Verificato T03 follow-up |
| A09 | Strumenti BC, interessi e facilities con collateral | T03/T07 | `test_finance.py`, policy accesso/cap/haircut e percorso browser; [report T07](reports/T07.md) | Verificato T03/T07 |
| A10 | Tasse, conto Tesoro, acquisti pubblici | T04 | `test_treasury.py`, run 53 settimane; [report T04](reports/T04.md) | Verificato T04 |
| A11 | Asta bond e acquisti BC effettivi | T04 | Prezzo marginale, pareggi, budget e invenduto in `test_treasury.py`; [report T04](reports/T04.md) | Verificato T04 |
| A12 | Scadenza pubblica, costo ammortizzato e deficit non finanziato | T04 | Rimborso dopo 52 settimane e default controllato in `test_treasury.py`; [report T04](reports/T04.md) | Verificato T04 |
| A13 | Quote societarie, diluizione e dividendi | T05 | Asta fallita/riuscita, pareggi, proprietari e dividendi in `test_equity_crisis.py`; scenario investimento CLI; [report T05](reports/T05.md) | Verificato T05 |
| A14 | Investimento reale e capacità da t+1 | T02/T05 | Acquisti al costo T02 e raccolta che compra capitale installato da t+1 in `test_scenario_equity_proceeds_buy_capital_effective_next_week`; [report T05](reports/T05.md) | Verificato T02/T05 |
| A15 | Default imprese, liquidazioni e perdite | T05 | Arretrati sanati, compratore reale/assente, riparto chirografario e quote in natura in `test_equity_crisis.py`; scenario crisi CLI; [report T05](reports/T05.md) | Verificato T05 |
| A16 | Risoluzione bancaria e distinzione liquidità/solvibilità | T05 | Caso `E=−20`, target 10, H 30, depositi insufficienti, prestiti persistenti, quote proprie e stress bancario CLI; [report T05](reports/T05.md) | Verificato T05 |
| A17 | Pausa, +1, +N, automatico e velocità | T06/T07 | Manuale/batch/automatico e pausa in corso | Runner e controlli UI verificati T06/T07; `PAUSING` osservato nel browser |
| A18 | Comandi idempotenti e politiche a confine di step | T06 | Duplicati, concorrenza e settimana assegnata | Verificato T06; [report](reports/T06.md) |
| A19 | Step atomico, errori e terminazioni distinti | T06 | Rollback in fase risorse/commit T02 e crisi T05, default sovrano T04 e crisi bancaria irrisolta T05; runner in T06 | Core e runner verificati T02/T04–T06; [report T06](reports/T06.md) |
| A20 | Checkpoint/ripresa deterministica | T06 | 100 vs 40+60 e checksum | Verificato T06; [report](reports/T06.md) |
| A21 | API, snapshot e riconnessione | T06/T07 | Eventi persi, recupero e due schede | API/WebSocket T06 e due schede/reload/recupero storico browser T07 verificati; [report T07](reports/T07.md) |
| A22 | Dashboard, pannello BC, mercati e agenti su dati reali | T07 | Percorso browser e ispezione UI | Verificato T07 su build FastAPI a 430/1280 px, politica pendente/attiva e dati motore; [report](reports/T07.md) |
| A23 | Salvataggi ed export di tutte le settimane | T06/T07 | CSV completo T02/T05 e cronologia eventi T05 nel JSON CLI; [report T05](reports/T05.md) | UI salva/carica in pausa e CSV scaricato uguale al server; [report T07](reports/T07.md) |
| A24 | Metriche definite: CPI/PIL, lavoro, credito, distribuzione | T08 | [Dizionario T02-v1](technical/t02_contracts.md), CPI imputato, bridge PIL esatto e dati reali; [report T02](reports/T02.md) | Metriche operative T02 verificate; completamento statistico e controparti future non verificati |
| A25 | Scenari e almeno cinque seed nei principali | T08 | Report riproducibile, inclusi collassi | Non verificato |
| A26 | Baseline 260 settimane, prestazioni misurate | T08 | Tempi, p95, memoria, macchina/versioni | Non verificato |
| A27 | Installazione locale e build servita da backend | T09 | Installazione pulita e smoke test | Non verificato |
| A28 | Target Windows e istruzioni macOS/Linux | T09 | Piattaforme testate e limiti dichiarati | Non verificato |
| A29 | Niente feature D2/D3 fittiziamente funzionanti | T07/T09 | Audit UI, scope e README | Audit UI T07 verificato; controllo finale T09 aperto |

## Regole per l'evidenza

- Un nome di test non prova il superamento: riportare comando eseguito, risultato e versione del codice.
- Se un ambiente non permette una prova, indicare NON ESEGUITO e motivare; non segnarla verificata.
- I report possono essere creati in `docs/reports/` durante lo sviluppo. Non creare adesso risultati vuoti che sembrino report eseguiti.
- Una revisione documentale prova coerenza delle istruzioni, non funzionamento o plausibilità empirica del simulatore.
- Quando cambia una feature già verificata, rivalutare le prove interessate; non ripetere indiscriminatamente l'intera suite se non risolve un rischio concreto.

## Accettazione finale

T09 può dichiarare D1 completo soltanto quando le righe pertinenti sono verificate e i criteri riferimento §14.4 soddisfatti. Se il lavoro è pronto ma manca un gate ambientale, consegnare il risultato descrivendo il gate ancora aperto senza falsificare lo stato.

## Requisiti prestazionali aggiunti nell'integrazione

| ID | Requisito | Task | Evidenza richiesta | Stato corrente |
|---|---|---|---|---|
| A30 | Stato per colonne e layout compatibile NumPy | T01 | `test_column_mapping_isolation_and_no_duplicate_balances`; [contratti](technical/t01_contracts.md) | Verificato T01 |
| A31 | Kernel batch con riferimento scalare | T02/T08 | Riferimenti scalari a 1/257/5.000 righe in `test_real_kernels.py`; [report T02](reports/T02.md) | Equivalenza kernel T02 verificata; profiling T08 non eseguito |
| A32 | Precisione monetaria e buffer/rollback coerenti | T01/T06 | Budget esatti T01/T02, pareggi microquote/UM e rollback stato quote/crisi/eventi T05; [report T05](reports/T05.md) | Core e concorrenza/checkpoint verificati T01–T06; [report T06](reports/T06.md) |
| A33 | Profiling e benchmark di scala | T08 | Costi per fase, kernel vs end-to-end, 10.000/52 e stima 100.000 | Non verificato |
