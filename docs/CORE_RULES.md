# Vincoli condivisi — leggere per ogni task

Questo riepilogo è normativo per il workflow e sintetico per l'economia; i dettagli e le eccezioni sono nei moduli collegati dall’[indice](INDEX.md). Non espanderlo in una seconda specifica. Segnalare le divergenze e correggere insieme i documenti.

## Prodotto e perimetro

- D1 è una webapp locale in italiano: Python indipendente, FastAPI, React/TypeScript/Vite, grafici proposti Recharts. Target iniziale Windows, istruzioni anche macOS/Linux.
- Economia chiusa: un Governo, una banca centrale, una valuta UM, più persone/imprese/banche. Il giocatore controlla la banca centrale; fiscalità e shock reali sono parametri di scenario separati.
- Popolazione adulta costante nel D1. Nascite/morti, nuove imprese, zecca, mercati secondari, multiplayer e AI negli agenti sono fuori scope.
- Prezzi, salari e rendimenti devono derivare da offerte, scelte e scambi; ammettere razionamento. Non imporre inflazione, disoccupazione o crescita per ottenere grafici convincenti.

## Architettura

- Il core non importa API o frontend, non dorme e non legge l'orologio reale per decisioni economiche.
- Un solo worker possiede lo stato; API e UI leggono snapshot conclusi. Un solo processo backend nel D1, niente multiworker che duplichi lo stato.
- Regole decisionali separate da dati degli agenti; transazioni eseguite tramite il ledger e settlement comune.
- Salvataggi versionati, RNG espliciti, IDs stabili e ordine deterministico; niente pickle arbitrario o `hash()` per decisioni riproducibili.
- Test e benchmark devono usare il percorso reale del motore. Fixture fittizie sono ammesse nei test isolati, mai per dichiarare completata l'applicazione.

## Tempo

- 1 step = 1 settimana; 52 settimane = anno del modello. La velocità modifica solo il ritmo di esecuzione.
- Pausa termina al massimo lo step in corso; +N è interrompibile. Nessuna settimana saltata e nessuna mutazione economica concorrente.
- Politiche applicate al primo confine futuro disponibile; comunicare la settimana assegnata. Comandi idempotenti con ID e sequenza server.
- Step atomico: validare e pubblicare solo a fine step; rollback di stato e RNG su errore software. Crisi economica terminale e errore software sono distinti.
- Stesso seed/config/versione/comandi economici produce gli stessi risultati a velocità diverse e dopo checkpoint/ripresa.

## Contabilità e unità

- Partita doppia e attività = passività + patrimonio per entità. Gli importi del ledger sono Decimal quantizzati a 0,000001 UM; quantità float64 con tolleranze documentate.
- Persone/imprese usano depositi; banche riserve presso BC; Tesoro conto separato presso BC. Niente copie indipendenti `cash`/depositi.
- Un prestito crea credito e deposito; non crea riserve e non presta riserve alle famiglie. Ogni pagamento interbancario regola anche riserve.
- Pagamento e consegna atomici; fondi/inventari vincolati non spendibili due volte. Recuperi da liquidazione solo se realmente realizzati o trasferiti in natura con scrittura.
- Svalutazioni, capitale delle banche, quote degli azionisti e perdite dei depositanti devono riconciliarsi. Rifinanziamento non equivale a ricapitalizzazione.
- Non correggere uno sbilancio con denaro gratuito o azzeramenti silenziosi. Patrimonio negativo può esistere e richiede trattamento esplicito.
- Stock a fine settimana, flussi settimanali, tassi annui effettivi convertiti con `(1+r_a)**(1/52)-1`. I nuovi prestiti maturano interessi dalla settimana successiva.

## Mercati e sequenza

- Sette prodotti finali: cibo, energia domestica, mobilità, abbigliamento, intrattenimento, viaggi, lusso. Tre risorse: energia all'ingrosso, materiali, metalli. Un bene capitale aggregato.
- Primari/secondari sono famiglie di mercati, non beni perfettamente sostituibili. Ogni mercato ha offerta, domanda, prezzo, matching, settlement e statistiche di mancata esecuzione.
- Salari emergono dal matching; credito da offerte e vincoli; bond zero coupon 52 settimane e nuove quote da aste primarie uniformi. Nessun rendimento pubblico fisso imposto.
- La produzione usa lavoro pagabile, capitale e input fisici. Estrattive non energetiche usano energia già in scorta; energia acquistata in t serve da t+1. Capitale acquistato in t diventa produttivo da t+1.
- Ordine normativo: apertura/politiche → servizio finanziario → Tesoro → piani/credito → lavoro/salari → estrazione → risorse → produzione → beni finali → investimenti → chiusura operativa → crisi → risultati/distribuzioni → commit. Dettagli in riferimento §10.
- Durante l'implementazione incrementale, le fasi non ancora realizzate sono esplicitamente disattivate nei profili di test; non sostituirle con denaro, scambi o dati impliciti. D1 richiede tutte le fasi attive pertinenti.

## Verifica e chiusura del task

- I moduli correnti sono la fonte normativa delle regole; le schede task stabiliscono scope ed evidenze. Una decisione registrata non autorizza a contraddire silenziosamente i moduli normativi.
- Parametri ancora da calibrare sono scelte di T01/T08, non fatti osservati. Documentare formula, unità, default e motivazione.
- Testare identità, casi limite e integrazione. Un effetto macro atteso non è una garanzia universale: non forzarlo nel codice.
- Aggiornare piano, decisioni e matrice di accettazione. Separare implementato, verificato e non eseguito. Non segnare D1 completo prima di T09 e delle prove richieste.
- I comandi esatti di installazione, test e build vengono ricavati dal progetto realmente creato; nessun comando immaginario può essere prova di completamento.

## Predisposizione NumPy

Stato numerico omogeneo per colonne dal T01; IDs stabili separati dagli indici. Kernel batch per calcoli indipendenti, settlement/ledger autorevole separato e senza float monetari definitivi. Non duplicare dati in oggetti e array né usare `np.vectorize` come promessa di accelerazione. Ordine degli scambi, casualità e risultati devono restare coerenti. Il modulo [performance_and_vectorization.md](technical/performance_and_vectorization.md) definisce layout, memoria, test e benchmark.
