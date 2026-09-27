# Efficienza e predisposizione a NumPy

**Requisito esplicito del proprietario, 27 settembre 2026.** Architettura predisposta dal T01 a calcoli vettoriali; adozione progressiva dei kernel NumPy. Questo modulo è normativo per struttura dei dati e criteri prestazionali. Non modifica l'economia, l'ordine degli scambi o il ledger.

## 1. Scelta: motore ibrido

Le operazioni omogenee su molti agenti lavorano su array numerici; i mercati con razionamento sequenziale, il settlement e gli eventi discreti mantengono l'ordine previsto dal modello. «Agent-based» non richiede un oggetto Python pesante per ogni agente: identità e comportamento individuale possono essere rappresentati da righe/indici di tabelle numeriche.

Obiettivo immediato: evitare una riscrittura completa quando aumenta la popolazione. Non promettere un fattore di accelerazione senza benchmark e non introdurre GPU, JIT o calcolo distribuito nel D1.

## 2. Stato per colonne, con una fonte autorevole

T01 definisce contenitori `HouseholdState`, `FirmState`, `BankState` (nomi indicativi), con colonne omogenee e shape/dtype documentati. Per ogni proprietà numerica frequentemente elaborata in blocco usare array NumPy fin dall'inizializzazione; algoritmi iniziali possono ancora iterarne gli indici.

| Dato | Rappresentazione proposta | Autorità |
|---|---|---|
| ID di agenti, banca, datore di lavoro, prodotto | `int64`, sentinella documentata per assenza | Registro/stato di dominio |
| Propensioni, produttività, qualità, quantità fisiche | `float64` con range e unità | Tabelle numeriche |
| Alive/active/employed, ammissibilità | Array booleani; chiarire flag persistenti vs maschere derivate | Stato o output della fase |
| Bisogni e inventari | Matrice agenti × piccolo numero di prodotti oppure colonne per prodotto | Registro fisico numerico |
| Depositi, debiti, riserve, valori contabili | `Decimal` nel ledger D1, accesso tramite servizi | Ledger soltanto |
| Numeri di contratto e collegamenti | Tabelle con ID di debitore/creditore e lookup | Registro contratti |
| Nomi/testi/metadati rari | Dizionari/record separati dal percorso numerico | Registro descrittivo |

ID stabile diverso dall'indice di riga: mantenere mapping ID→row, maschere attive e ordinamenti espliciti. Fallimenti non devono rinumerare gli ID o modificare l'ordine casuale implicitamente. Predisporre crescita delle tabelle per D2 senza implementare demografia ora.

Classi di dominio/dataclass ammesse come contenitori di array o viste su una riga, non come seconda copia mutabile degli stessi numeri. Nessun sincronizzatore bidirezionale fra oggetti e array. Evitare a ogni step conversioni complete lista di oggetti→DataFrame→array→oggetti. pandas resta destinato a report/analisi/export, non al nucleo di aggiornamento settimanale.

## 3. Separare calcolo e applicazione

Ogni funzione numerica riceve array, parametri e, se necessario, estrazioni casuali già prodotte. Restituisce intenzioni/quantità/maschere. Il servizio di mercato valida, alloca e il settlement applica i pagamenti. Interfaccia concettuale:

```text
stato disponibile → kernel numerici → intenzioni/ordini
→ matching nella sequenza prevista → settlement → nuovo stato
```

I kernel non modificano direttamente il ledger e non invocano metodi per agente nascosti dentro funzioni apparentemente vettoriali. API/frontend rimangono indipendenti dal layout interno. La dimensione del batch è un parametro tecnico: non deve cambiare la settimana economica o la politica di allocazione.

## 4. Candidati e limiti

| Operazione | Approccio iniziale |
|---|---|
| Bisogni, buffer, obiettivi di consumo, segnali di prezzo | NumPy per formule indipendenti fra agenti |
| Capacità/output potenziale da lavoro e input | `minimum`, maschere e operazioni per colonne |
| Indicatori di soddisfazione, distribuzioni, aggregati fisici | Riduzioni NumPy; definire mancanti e ordine di riduzione |
| Valutazioni del credito e score dei fornitori | Calcolo in blocco; concessione/allocazione successiva con vincoli aggiornati |
| Matching con inventari e budget che cambiano dopo ogni trade | Mantiene l'ordine sequenziale normativo; vectorizzare solo parti indipendenti |
| Aste | Ordinamento/score in array possibili; spareggi, budget e prezzo marginale invariati |
| Pagamenti, default, liquidazioni, scritture | Operazioni esplicite o batch atomici con contropartite; nessuna semplice assegnazione massiva ai saldi |

`np.vectorize` non è una strategia di accelerazione: è un wrapper di comodità intorno a chiamate Python. Usare operazioni NumPy native e dtype numerici, evitando `dtype=object` nei percorsi numerici intensivi. Un array di oggetti Decimal non rende vettoriale la contabilità.

## 5. Precisione monetaria

Il ledger resta Decimal a 0,000001 UM nel D1. Le proiezioni monetarie `float64` per score/stime sono viste di calcolo derivate, temporanee e non autorevoli. Al confine con un ordine, convertire/quantizzare con regola documentata, poi verificare budget esatto e risorse residue; i fondi non possono diventare negativi per arrotondamento. Definire tie-break deterministici vicino alle soglie.

Metriche contabili e somme che devono riconciliarsi si calcolano sul ledger esatto. Un eventuale motore contabile futuro a interi scalati `int64` può migliorare prestazioni, ma richiede decisione tecnica separata, controlli di overflow di somme/prodotti, scale e arrotondamenti. Non sostituire silenziosamente Decimal con float per guadagnare velocità. Separare oggi l'interfaccia del ledger rende possibile quella migrazione senza riscrivere le regole degli agenti.

## 6. Memoria, complessità e atomicità

- Vietato costruire indiscriminatamente una matrice di tutte le persone contro tutte le imprese: partizionare per prodotto, filtrare candidati e usare blocchi limitati. Broadcasting può creare output enormi anche se gli input non sono copiati.
- Specificare se una funzione riceve una vista o una copia, e chi può scrivere. Una vista condivisa non è uno snapshot immutabile; il worker non deve modificare buffer esposti al frontend.
- Evitare concatenazioni ripetute di array nella sessione di scambi: usare buffer preallocati/chunk o raccogliere dati e concatenare una volta.
- Il rollback non copia tutta la cronologia/ledger dall'inizio a ogni settimana. Separare stato corrente da storico append-only; usare staging/delta/undo del singolo step o copia limitata allo stato corrente, con test di errore a metà fase.
- Le scritture/evidenze necessarie restano conservate. Lo storico può essere persistito in file a chunk, con offset/manifest versionati; niente eliminazione silenziosa di settimane per liberare RAM. Un checkpoint deve includere o riferire in modo portabile tutti i dati necessari alla ripresa, e l'import li deve validare.
- Dashboard riceve aggregati e dettagli paginati. Frequenza grafica e campionamento visivo non cambiano lo storico economico esportato.

## 7. Riproducibilità e equivalenza

T01 crea stream RNG nominati per sottosistema, derivati dal seed con mapping stabile e salvati nei checkpoint. Non assegnare stream in base all'ordine accidentale di creazione dei moduli. Le fasi prelevano estrazioni in ordine documentato rispetto agli ID; il refactoring in blocchi non deve cambiare l'abbinamento agente/estrazione.

Per ogni kernel ottimizzato mantenere una semplice implementazione scalare di riferimento nei test. Con stessi input ed estrazioni confrontare output: contabilità/discreto esatti, quantità floating entro tolleranze dichiarate. Soglie, sort e spareggi devono conservare la semantica; una differenza che altera l'allocazione non può essere giustificata solo come «piccolo errore numerico».

Determinismo manuale/automatico e checkpoint resta richiesto per stessa versione/backend/ambiente numerico dichiarato. Non promettere identità bit-per-bit fra architetture, versioni NumPy o ordine diverso delle riduzioni. Se cambia una semantica o sequenza RNG, versionare il motore e dichiarare l'incompatibilità, non qualificare la modifica come mera ottimizzazione.

## 8. Piano e misure

- **T01:** contenitori per colonne, IDs/row mapping, ledger isolato, RNG per fase, schema numerico; niente motore alternativo completo.
- **T02:** almeno bisogni/soddisfazione e output potenziale in funzioni batch; controlli con riferimento scalare e casi limite.
- **T03–T05:** scoring in blocco dove utile; allocazioni e scritture preservano gli ordini.
- **T06:** snapshot/rollback senza copiare tutto lo storico; buffer correttamente isolati e salvataggi portabili.
- **T08:** misurare profilo per fase, numero di agenti/contratti/trade, costo del ledger, conversioni, memoria di picco e payload UI; ottimizzare il collo di bottiglia effettivo.

Mantenere il benchmark obbligatorio D1 da 1.000 persone/260 settimane. Aggiungere uno smoke benchmark di scala da 10.000 persone/52 settimane, con capacità/imprese/spesa ridimensionate secondo regola dichiarata e invarianti attive. Se il run termina economicamente, riportarlo e distinguere quel limite dai tempi computazionali. Per 100.000 persone è sufficiente una stima di memoria/complessità nel D1; non è un nuovo requisito di throughput né obbligo di esecuzione.

Confrontare kernel scalare/NumPy su almeno due dimensioni, escludendo preparazione dati solo se riportata separatamente; misurare anche end-to-end. Se NumPy rallenta un caso piccolo, documentarlo. La crescita delle tabelle, la conversione monetaria e il ledger possono dominare il costo: non attribuire miglioramenti al solo numero di loop eliminati.

## 9. Fonti tecniche

Consultate il 27 settembre 2026. La struttura ibrida, il layout dei dati e i gate sopra sono scelte specifiche del progetto.

- [NumPy: broadcasting](https://numpy.org/doc/stable/user/basics.broadcasting.html): operazioni fra array e limiti di memoria.
- [NumPy: vectorize](https://numpy.org/doc/stable/reference/generated/numpy.vectorize.html): wrapper di comodità, non ottimizzazione.
- [NumPy: copie e viste](https://numpy.org/doc/stable/user/basics.copies.html): proprietà e condivisione dei buffer.
- [NumPy: stream casuali](https://numpy.org/doc/stable/reference/random/parallel.html): stream derivati mediante SeedSequence.
