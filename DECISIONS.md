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

Le decisioni derivate dall'implementazione T01 sono registrate sotto; nessun benchmark macro è ancora stato eseguito.

## Integrazione documentale 3.2

- D016 — Fonte unica per argomento: i moduli in docs/model e docs/technical contengono le regole; SPEC è una panoramica e INDEX la mappa. Le schede task richiamano i moduli. Motivazione: lettura selettiva senza doppia manutenzione.
- D017 — Conservazione dei contenuti: le regole economiche 3.1 restano la baseline; v2 conservata solo come archivio storico. Il ciclo vecchio e i regimi monetari immediati della v2 non sostituiscono quelli aggiornati.
- D018 — Nessun gate decisionale nuovo per iniziare T01. I tre orientamenti di prodotto più rilevanti hanno default espliciti in docs/PRODUCT_DECISIONS.md; un cambio sostanziale richiede aggiornamento dei moduli e dei task interessati.

Le scelte residue I001–I009 sono dettagli tecnici/calibrazioni assegnati agli sviluppatori; non richiedono nove domande preventive al proprietario.

## Requisito aggiunto durante l'integrazione

- D019 — Richiesta esplicita del proprietario: predisporre il simulatore al calcolo vettoriale NumPy e all'efficienza. Adottato dal T01 layout per colonne e kernel separati; implementazione ibrida progressiva, non riscrittura futura obbligata. Specifica in docs/technical/performance_and_vectorization.md.
- D020 — Il ledger D1 rimane Decimal; NumPy tratta calcoli numerici e proiezioni non autorevoli. Un futuro ledger a interi scalati è una migrazione tecnica da misurare/validare separatamente, non una scelta imposta ora al proprietario.

I010 — T01 documenta layout/dtype/RNG e confine monetario; T02 implementa i primi kernel; T06 atomicità efficiente; T08 profila e misura la scala. Nessuna decisione bloccante del proprietario su dettagli NumPy.

## Decisioni implementative T01 — 27 settembre 2026

- **D021 — Toolchain Python.** Python 3.11.9, `uv` 0.7.5 verificati su Windows; NumPy 2.2.6, Pydantic 2.11.10, PyYAML 6.0.3, pytest 8.4.2 e Ruff 0.11.13 risolti in `uv.lock`, build Hatchling 1.27.0. Scelta conservativa di una sola minor Python al posto di compatibilità non provata. Nessuna dipendenza API/frontend. I001 risolto per Python; Node resta T07. Test, CLI, build e installazione wheel nel report.
- **D022 — Calibrazione e scala di apertura.** Catalogo completo con 11 prodotti, ricette esplicite, due cicli di input iniziali, capitale e giacimenti ereditati. Scala per impresa `N/N_ref × C_ref/C`, posti arrotondati per eccesso, cassa/capitale bancario/spesa pubblica pro capite. Alternativa respinta: stock campionati indipendentemente o capacità invariante al crescere della popolazione. Numeri, unità e motivazioni nei [contratti T01](docs/technical/t01_contracts.md); test base, input incompatibili e scale 100/123/2.000 persone. I002 definito, da calibrare in T08.
- **D023 — Controparti di apertura e proprietà.** Riserve di ogni banca = suoi depositi + capitale sottoscritto; BC detiene un bond ereditato alla pari che copre riserve e Tesoro. Patrimonio iniziale del Governo negativo ed esplicito; nessun conto di suspense. Imprese possiedono depositi, scorte e capitale al costo; ogni emittente ha un proprietario scelto da una permutazione delle persone. È una proprietà iniziale concentrata, sostituibile con distribuzione diffusa se richiesta da calibrazione. I003 risolto; I005 risolto per cassa/nominale di apertura e parametri fiscali, meccanismi T04. Verifiche per ogni entità/strumento/partecipazione, nessuna correzione monetaria implicita.
- **D024 — Autorità monetaria e stato numerico.** Ledger Decimal, contesto locale a 50 cifre e arrotondamento half-even al micro-UM; proiezioni float64 temporanee immutabili. ID stabili separati dalle righe; matrice fisica con 11 colonne, dataclass solo per contenitori/viste. Copie immutabili preferite alle viste condivise; nessuna promessa di accelerazione. Posting prepara delta/nuovi conti, senza copiare il journal; validatore diagnostico completo. I010 completato per T01. Test su aliasing, budget, riserve insufficienti e consegna atomica.
- **D025 — Contratti incrementali e determinismo.** Profilo `initialization_only` con tutte le fasi future false; nessuno step fittizio. Stream PCG64 nominati con numeri stabili, canonical JSON/SHA-256 e versioni schema/layout 1. Metadati di run e runtime esclusi dal checksum. Round trip degli schemi e degli stati RNG, esportazione diagnostica, niente import checkpoint anticipato. I007 risolto per contratti minimi; runner, idempotenza e ripresa restano T06.

Stato residuo: **I004 parziale**, propensioni/buffer e parametri bancari di base espliciti; regole e limiti decisionali T02/T03, calibrazione T08. **I006 resta T02/T08**: T01 registra costi delle dotazioni e primitive di vendita, senza produzione/PIL. I008/I009 non anticipati. Nessuna modifica al perimetro D1 o alle regole normative. Evidenze complete: [report T01](docs/reports/T01.md).

## Decisioni implementative T02 — 27 settembre 2026

- **D026 — Profilo reale incrementale esplicito.** `real_economy` attiva soltanto le fasi implementate; tasse, spesa e interessi zero, facilities disabilitate. Il bond ereditato T01 rimane congelato come contropartita delle riserve, senza servizio/emissione neppure alla settimana 52. Alternativa respinta: cancellare il debito d'apertura e sbilanciare il patrimonio, oppure simulare un Tesoro implicitamente finanziato. Fasi future e sottofasi non realizzate sono tracciate nei no-op. Schema, CLI e test di profilo documentati nei [contratti T02](docs/technical/t02_contracts.md).
- **D027 — Budget e consumo da patrimonio.** Separati risparmio sul reddito, buffer legato ai primari e prelievo esplicito dal patrimonio. Budget primari e secondari proporzionali ai rispettivi costi; scorte mancanti non liberano budget per lusso nella stessa settimana. Lusso con intenzione logaritmica crescente e concava, senza tetto fisico ma con budget finito. Alternativa respinta: usare tutti i depositi come reddito o introdurre quantità infinite. Nessun cambiamento alle estrazioni T01. Kernel batch e priorità verificati; formule/default nel contratto.
- **D028 — Piani e matching osservabili.** Ricette, unità e deperimenti T01 confermati senza ricalibrazione. Dopo il bootstrap, piani da vendite più domanda finanziabile non evasa, distribuita una sola volta fra venditori. Prezzi con segnali/costi laggati; costi smussati, variazioni limitate. Matching per prodotto, score adimensionale, permutation RNG e fornitori alternativi; salario emergente con contratti revisionati ogni 13 settimane e paga anticipata. Turni non finanziabili sospesi prima della prestazione, senza lavoro gratuito. Scelte semplici in alternativa a previsioni perfette o mobilità avanzata; test lavoro, scarsità, prezzi e riserve.
- **D029 — Inventari e capitale al costo.** Salari pagati in lavorazione, input al costo medio; produzione carica output, salari senza output spesati. Deperimento e ammortamento espliciti. Acquisti di macchinari direttamente in `pending_capital` al prezzo pagato, anche quando il compratore produce capitale; installazione soltanto all'apertura successiva. Evita la commistione con scorte di vendita e non anticipa emissioni T05. Test contabili di costo medio, mancanza dei fattori, estrazione e t+1.
- **D030 — Statistiche operative e bridge esplicito.** CPI con paniere configurato fisso, ultimo prezzo valido, quota imputata ed età; prezzo transato null senza scambi. PIL operativo con output invenduto al costo e margini realizzati, riconciliato indipendentemente con C+I+variazione scorte escludendo perdite. Eventuali differenze impediscono il commit, senza correzioni residuali. PIL reale a prezzi base separato. Alternativa respinta: sommare vendite intermedie o trattare un prezzo imputato come osservato. Dizionario T02-v1 nei contratti; revisione statistica e calibrazione rimangono T08.
- **D031 — Atomicità sincrona e versioni.** Motore 0.2.0, layout 2. Copia dello stato corrente e offset delle code append-only per l'undo; nessuna copia del journal storico. Errore ripristina anche RNG e stato numerico, impedisce altri step e conserva la diagnosi. Validazione corrente a ogni commit e completa alla chiusura CLI. Contratti snapshot estesi per metriche negative/null e mercati reali; replay 0.1.0 non promesso. Test di eccezione a metà fase e al commit, isolamento delle letture, determinismo e round trip. Runner, concorrenza e checkpoint restano T06.

Stato residuo: **I004 risolto per le decisioni T02**, credito T03 e calibrazione T08 ancora aperti. **I006 implementato/verificato per inventari e PIL operativo T02**, revisione statistica T08 aperta. **I010 verificato per i kernel T02**, profiling/scala T08 aperti. Il run 1.000 persone/52 settimane termina senza errori software ma con collasso dell'attività: non è stato mascherato né usato per dichiarare D1 robusto. Evidenze e diagnosi nel [report T02](docs/reports/T02.md).

## Decisioni implementative T03 — 28 settembre 2026

- **D032 — Prezzo e razionamento del credito.** Score annuale logistico batch, poi limiti esatti sequenziali su capitale, concentrazione, debt/income, copertura e liquidità. Una richiesta ha ID idempotente e una sola erogazione, anche parziale. I coefficienti/default sono nei contratti T03 e restano da calibrare in T08.
- **D033 — Facilities e policy.** Policy attiva distinta dalla coda futura; corridoio validato a ogni modifica. Facility settimanali con haircut 5% sui bond e 35% sui prestiti performing, cap 50% degli asset e hold autorevole sul collateral. Il settlement T03 tenta il rifinanziamento prima del rifiuto; T02 resta invariato.
