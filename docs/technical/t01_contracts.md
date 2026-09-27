# Contratti implementati da T01

Versioni: motore `0.1.0`, configurazione/JSON/layout `1`. Questo documento descrive il codice consegnato, senza sostituire i moduli normativi. Le API future restano in [api_contracts.md](api_contracts.md).

## Configurazione e calibrazione iniziale

`load_config(path)` legge scenario e catalogo, risolvendo `products_file` relativamente allo scenario. `Config`, `ScenarioFile` e `Catalog` in `src/economic_sim/config.py` sono gli schemi eseguibili; `model_json_schema()` permette di ispezionarli. Tutti i campi dello scenario e del catalogo sono obbligatori, salvo i campi facoltativi delle patch di comando. `configs/base.yaml` e `configs/products.yaml` contengono i valori proposti, non osservazioni empiriche.

Campi sconosciuti, chiavi YAML duplicate/non testuali, coercizioni stringa→numero, booleani al posto di ID, NaN/Inf, prezzi non positivi e corridoi dei tassi invertiti vengono rifiutati. Importi/prezzi UM si scrivono come stringhe decimali (oppure interi), non float YAML; tassi e quantità sono numerici. Il tasso annuo effettivo deve superare −1 e la conversione è `expm1(log1p(r)/52)`.

Le impostazioni `features`, BC, fiscalità e banche dichiarano lo scenario D1 desiderato. Il profilo `initialization_only` richiede **tutte** le dodici fasi economiche esplicitamente false: quei flag non rendono operativi mercati o facilities. Parametri decisionali aggiuntivi saranno introdotti insieme alle rispettive regole in T02–T05.

| Blocco | Unità/formula dei valori proposti | Motivazione |
|---|---|---|
| `simulation` | 1.000 adulti, 3 banche, 3 imprese per ciascuno degli 11 prodotti; seed 42 | Baseline richiesta, ID e scala riproducibili |
| `runtime` | Settimane/secondo e aggiornamenti UI/secondo | Solo contratto futuro; escluso dal checksum economico |
| `people.initial_deposit` | 1.000 UM × uniforme [0,75; 1,25] | Eterogeneità di liquidità ereditata |
| Età, propensioni | Età intera in settimane tra 18 e 65 anni inclusi; tre uniformi [0,1; 0,9] | Tutti adulti, varietà senza estremi obbligati |
| Salario di riserva | 100 UM/settimana × uniforme [0,8; 1,2] | Stima iniziale; reddito atteso e impiego partono da zero |
| Buffer, prelievo da patrimonio | 2 settimane di primari; 0,05 del patrimonio disponibile | Parametri di consumo per T02, nessuna sottrazione contabile all'avvio |
| Imprese | Deposito 10.000 UM; salario offerto 120 UM/persona-settimana; reputazione 0,5 | Prima busta paga finanziabile; nessun contratto di lavoro implicito |
| Banche | Capitale totale 150 UM × popolazione; rapporto minimo 0,08; pass-through 0,5 | Capitale ereditato e parametri futuri; nessuna concessione automatica di credito |
| Tesoro | Cassa 100 UM × popolazione; budget futuro 5 UM/persona-settimana | Cassa separata e spesa scalabile; pesi cibo/energia/mobilità 0,5/0,3/0,2 |
| Fiscalità | Lavoro 0,20, profitto 0,25; bond 52 settimane; rendimento massimo futuro 0,25 | Default di laboratorio; nessuna tassa o asta ancora eseguita |
| BC | Tassi 0,02/0,03/0,05; budget acquisti 0 UM; prezzo massimo 1 UM/nominale | Corridoio coerente; facilities dichiarate ma disattivate dal profilo |
| Quote | 1.000 quote per emittente, incluse banche | Un proprietario iniziale per emittente, scelto dalla permutazione delle persone; riuso ciclico se necessario |

Catalogo completo in `products.yaml`: `recipe` esprime unità di input per unità di output; `productivity` unità/persona-settimana; `capacity_per_capital` unità/(unità capitale × settimana). `depreciation` è la frazione fisica persa a settimana; per i servizi vale 1. Tutte le imprese ereditano 60 unità di capitale alla scala di riferimento. Il suo costo unitario iniziale è 50 UM, distinto dal prezzo offerto di 100 UM; il suo deperimento 0,001 servirà anche all'ammortamento fisico delle immobilizzazioni. I giacimenti sono stock naturali non prodotti, registrati fisicamente con valore contabile iniziale zero.

I bisogni primari sono 10/5/3 unità per persona-settimana. I secondari hanno distribuzioni normali **troncate per rigetto** a zero, con (media, deviazione) abbigliamento (0,2; 0,1), intrattenimento (0,5; 0,2), viaggi (0,1; 0,05). Il lusso ha `unlimited_need=true`: nella matrice il valore zero è un segnaposto strutturale, non un tetto di domanda; nessun infinito entra negli ordini.

Alla scala di riferimento i posti pianificati sono 393, senza assunzioni eseguite. Le capacità dei primari coprono i fabbisogni iniziali se il lavoro sarà effettivamente assunto e pagato. Ogni ricetta ha due cicli di input in scorta, calcolati rispetto a `min(K × capacity_per_capital, productivity × initial_workers)`. Energia domestica e all'ingrosso sono distinte; materiali/metalli usano energia ereditata; il lusso usa metalli. Il bootstrap verifica prodotti, input, giacimenti, forza lavoro e monte salari iniziale; non garantisce vendite o equilibrio futuro.

Per popolazione `N` e `C` imprese per prodotto, il fattore per impresa è `s = N/reference_population × reference_companies_per_product/C`. Depositi d'impresa, scorte, capitale e giacimenti sono moltiplicati per `s`; i posti per impresa sono `ceil(initial_workers × s)`. La capacità aggregata e le dotazioni pubbliche/bancarie crescono quindi con `N`; aumentare `C` suddivide la capacità. Produttività, prezzi, salario, bisogni pro capite restano invariati. Scorte e forza lavoro vengono ricontrollate dopo l'arrotondamento dei posti. I residui monetari del capitale bancario vanno alle banche in ordine di ID, un micro-UM alla volta.

## Ledger e apertura

Il ledger è l'unica autorità di depositi, riserve, debiti e valori contabili. `AccountKind` distingue attività, passività, patrimonio, redditi e spese. Le scritture hanno segno dare positivo; `balance(account)` restituisce il saldo con il segno naturale del conto. Ogni transazione deve bilanciare **per entità**, oltre a rispettare i conti non negativi e i vincoli sui fondi. Gli account contengono proprietario, controparte, finalità e ID dello strumento; la transazione contiene ID comune, settimana, fase e causale.

Precisione 0,000001 UM, `ROUND_HALF_EVEN`, contesto Decimal locale a 50 cifre, importi assoluti inferiori a 10²⁴ UM. Il posting rifiuta Decimal non quantizzati e float; il servizio quantizza gli importi e ricontrolla il budget esatto. Il journal è append-only; una transazione prepara soltanto i delta e i conti nuovi e li pubblica dopo tutte le verifiche. Non copia lo storico per tentare un pagamento. Il validatore diagnostico T01 rilegge invece il journal per riconciliarlo con i saldi; la validazione incrementale di step sarà compito delle milestone successive.

Definendo `D_b` come depositi dei clienti della banca `b`, `E_b` come suo capitale e `T` come cassa del Tesoro:

| Entità | Attività di apertura | Passività | Patrimonio |
|---|---|---|---|
| Banca b | Riserve `R_b = D_b + E_b` | Depositi `D_b` | Capitale sottoscritto `E_b` |
| BC | Bond pubblico `B = ΣR_b + T` | Riserve `ΣR_b` e conto Tesoro `T` | Zero |
| Governo | Conto Tesoro `T` | Bond `B` | Patrimonio ereditato `−ΣR_b` |
| Impresa | Deposito + input/output al costo + capitale installato al costo | Nessun prestito iniziale | Capitale sottoscritto pari alle attività |
| Persona | Deposito + partecipazioni al costo storico | Nessun debito iniziale | Patrimonio ereditato pari alle attività |

Il bond ereditato è iscritto alla pari, con nominale unitario 1 UM e scadenza settimana 52. Non è il risultato di un'asta e non impone un rendimento alle emissioni future. Il prezzo di riferimento della prima asta è un parametro separato. Il patrimonio negativo del Governo è esplicito; non ci sono risorse estere, conti di suspense, depositi iniziali senza controparte o voci di reddito. Le azioni rappresentano il capitale sottoscritto: il costo storico del proprietario non si aggiorna automaticamente quando l'emittente realizza un profitto o una perdita.

`Settlement.originate_loan` e `repay_loan` sono primitive contabili alla banca del depositante, senza decisione creditizia. Il capitale residuo è letto dal ledger, non copiato nel contratto. Nuovi prestiti hanno `interest_from_week = originated_week + 1`; la maturazione vera degli interessi è T03. Il prestito crea deposito/debito e credito/passività per depositi; il rimborso li estingue senza cambiare riserve.

`transfer` registra un trasferimento esplicito (spesa del pagante/reddito del ricevente). `purchase` registra pagamento, ricavo, scarico al costo medio e inventario del compratore, nella stessa transazione del registro fisico; non effettua consumo o matching. Fra banche diverse vengono regolate entrambe le riserve e le passività BC. Errori distinti: `insufficient_customer_funds`, `bank_settlement_failure`, `insufficient_inventory`. Nessuna facility viene invocata in T01. ID di transazione duplicati sono rifiutati, senza un secondo effetto; l'idempotenza dei comandi del runner resta T06.

`reserve/release` vincola fondi o quantità fisiche. I pagamenti ordinari spendono solo disponibilità libere; T01 non espone ancora ordini di mercato che consumano automaticamente questi vincoli. Tutte le operazioni hanno un solo proprietario dello stato; nessun thread concorrente è supportato.

## Layout numerico e confine dei kernel

Gli ID stabili `int64` sono separati dal row index: BC 1, Governo 2, banche da 100, imprese da 1.000.000, persone da 10.000.000. I range non si sovrappongono ai massimi dello schema. `id_to_row` è una mappa di lettura; `NO_ID = −1` indica nessun datore di lavoro. Le righe non si rinumerano al cambio di stato operativo.

| Contenitore | Colonne/shape | Dtype e unità |
|---|---|---|
| `HouseholdState` | ID, banca, datore, età `(N,)` | int64; età in settimane |
| | active `(N,)` | bool persistente; tutti adulti attivi |
| | propensioni `(N,)`, needs `(N,11)`, satisfaction `(N,7)` | float64; propensioni/soddisfazione adimensionali, bisogni in unità/settimana |
| | reservation_wage, expected_income `(N,)` | float64, stime UM/settimana, mai saldi contabili |
| `FirmState` | ID, banca, prodotto, posti pianificati `(F,)` | int64; posti interi, prodotto unico |
| | active, extractive `(F,)` | bool persistenti |
| | produttività, salario/prezzo offerto, qualità/reputazione, ordini/vendite passati `(F,)` | float64; unità esplicite nel catalogo; offerte da quantizzare al settlement |
| `BankState` | ID `(B,)`, active `(B,)`, deposit_rate `(B,)` | int64, bool, float64 annuo effettivo |
| `PhysicalRegister` | inventory, installed_capital, natural_reserve `(N+F,11)` | float64 in unità del prodotto; capitali/giacimenti senza saldi monetari duplicati |
| Proiezione depositi | `(numero_ID_richiesti,)` | float64 UM, temporanea e non autorevole |

Gli input del costruttore vengono copiati. `column`, `quantities` e proiezioni restituiscono copie su buffer immutabili (anche `setflags(write=True)` è rifiutato); `replace_column` è l'accesso di scrittura riservato al proprietario dello stato, con controllo shape e finitezza. `AgentView` legge ogni deposito dal ledger al momento dell'accesso. Snapshot JSON e dizionari esportati sono copie staccate.

API dei kernel T02: array numerici di lettura + parametri espliciti + estrazioni casuali già prodotte → nuovi array di intenzioni, quantità o maschere. Nessun kernel modifica ledger, RNG o buffer esposti; il servizio traduce le intenzioni in ordini quantizzati e settlement sequenziale. Nessun kernel economico viene dichiarato implementato da T01. Non si costruiscono matrici persone×imprese; le matrici fisiche hanno soltanto 11 prodotti. Tolleranze fisiche di riconciliazione: assoluta `1e-9`, relativa `1e-12`; non autorizzano quantità negative né vendite eccedenti lo stock.

## RNG, serializzazione e snapshot

Generatori espliciti PCG64/SeedSequence, derivati da `[seed, numero_stream]`. Mappa stabile: people=1, endowments=2, ownership=3, labor=10, credit=11, goods=12, resources=13, bonds=14, equity=15. L'accesso a uno stream non avanza gli altri. All'apertura si ordinano prodotti e ID; lo stream persone estrae bisogni per prodotto, poi età, risparmio, rischio, qualità e salario, per righe crescenti. Endowments estrae i depositi e ownership una permutazione degli ID delle persone. I futuri mercati hanno già stream indipendenti; non sono eseguiti.

Gli stati RNG si esportano e ripristinano con validazione preventiva di tutti gli stream. Il JSON canonico ordina le chiavi, usa UTF-8, non accetta NaN/Inf, serializza Decimal a sei cifre decimali e array in ordine di riga. SHA-256 comprende configurazione economica, versioni, agenti, conti/journal, registro fisico, contratti, quote e RNG. Esclude `run_id`, runtime/velocità e metadati temporali; non usa `hash()` di Python. L'identità bit-per-bit è verificata nello stesso ambiente NumPy/Python, non promessa fra backend numerici diversi.

`Snapshot`, `Offer`, `Order`, `Trade`, `MarketResult`, `Loan`, `Bond`, `ShareIssue`, `ShareHolding`, `PolicyCommand` sono schemi minimi tipizzati, con round trip JSON. Gli snapshot T01 sono in pausa a settimana 0: aggregati monetari reali, mercati/eventi/comandi vuoti. `submitted_at` è metadato; settimana assegnata e contatore server sono già nel contratto, ma accettazione, idempotenza, calendario e trasporto sono T06. Il riepilogo CLI include tutti i bilanci, le scritture, bond, proprietà, inventari e checksum; è una diagnosi, **non un checkpoint ricaricabile**.

## Limiti e passaggio a T02

Nessuno `step()`, mercato dinamico, API HTTP o frontend. Non ci sono interessi maturati, tasse, svalutazioni, emissioni successive o liquidazioni. I nuovi conti di questi flussi andranno introdotti insieme alle controparti e alle invarianti. I giacimenti a costo zero e la proprietà iniziale concentrata sono semplificazioni dichiarate da calibrare. La sostenibilità dopo 52/260 settimane, l'allocazione effettiva del lavoro, la calibrazione macro e le prestazioni restano da verificare in T02–T09.
