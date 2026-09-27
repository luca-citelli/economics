# Metriche e definizioni

Documento normativo corrente (revisione 3.2). Riferimenti storici: §11. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 11. Metriche e definizioni

### 11.1 Prezzi e inflazione

Per ogni prodotto esporre prezzo medio ponderato per quantità delle transazioni, quantità, prezzo offerto medio, numero di scambi e copertura. Se non ci sono transazioni, il prezzo transato è `null`.

Indice dei prezzi a paniere fisso per categoria `c`:

`CPI_c,t = 100 × sum(p_i,t × q_i,0) / sum(p_i,0 × q_i,0)`.

Paniere di riferimento configurato e congelato alla settimana 0; prezzi iniziali dalle offerte iniziali esplicitamente marcate. Se manca un prezzo transato, usare per il solo indice l'ultimo prezzo valido (inizialmente quello di offerta) e mostrare quota del paniere imputata e anzianità del prezzo. Non confondere assenza di scambi con inflazione zero certa.

- Inflazione settimanale: `CPI_t / CPI_(t−1) − 1`.
- Inflazione annua osservata: `CPI_t / CPI_(t−52) − 1`, disponibile dalla settimana 52.
- Annualizzazione di una variazione settimanale, se mostrata: `(CPI_t / CPI_(t−1))^52 − 1`, etichettata separatamente perché volatile.

Prezzi aggregati possono risentire del mix qualità/fornitori: la qualità è fissa per impresa nel D1, ma cambia il mix delle vendite. Non chiamare questo indice un CPI ufficiale corretto edonicamente.

### 11.2 Attività reale e conti pubblici

- Produzione fisica per prodotto e utilizzo di capacità.
- PIL nominale operativo: somma del valore aggiunto dei settori produttivi, con inventari e produzione capitale registrati; servizi finanziari imputati esclusi nel D1, convenzione dichiarata.
- Controllo dal lato spesa: `C + I + G + variazione_scorte`, includendo le scorte intermedie e finali una sola volta, escludendo rivalutazioni/perdite di possesso. Non sommare semplicemente tutte le vendite fra imprese.
- Produzione/PIL reale a prezzi base con output e input valutati ai prezzi della settimana 0; non sommare unità eterogenee di cibo ed energia.
- Investimento reale = acquisti di capitale; sottoscrizioni di bond/azioni escluse dal PIL.
- Entrate fiscali, spesa pubblica, interessi maturati, deficit di competenza, saldo di cassa, debito nominale/contabile, emissioni e rimborsi.
- Debito/PIL usa 52 settimane di PIL; prima di allora è `N/D` oppure una stima annualizzata chiaramente etichettata.

Valorizzazione e bridge fra costo degli inventari e valutazione statistica devono essere documentati: eventuali discrepanze fra PIL produzione/spesa sono esposte, non nascoste con una voce residua arbitraria.

### 11.3 Famiglie, lavoro, credito e distribuzione

- Popolazione, occupati, forza lavoro, disoccupazione = disoccupati/forza lavoro.
- Reddito lordo/netto medio e mediano; reddito da lavoro, interessi e dividendi separati.
- Risparmio di flusso = reddito disponibile − consumi; depositi e ricchezza netta sono stock diversi.
- Gini dei redditi non negativi; per ricchezza con valori negativi usare quantili e quota detenuta, senza applicare ingenuamente lo stesso Gini.
- Soddisfazione per bisogno = `min(consumato / richiesto, 1)`; primari complessivi come minimo dei tre rapporti, più quota di persone che supera la soglia su tutti.
- Lusso consumato, persone in privazione, durata della privazione.
- Depositi, riserve, prestiti per settore, nuove erogazioni/rimborsi, tassi nuovi ed esistenti, arretrati, default, rifiuti per motivo.
- Banche: patrimonio, leva, riserve, liquidità disponibile, collateral vincolato, debito BC, perdite e risoluzioni.
- Imprese: ricavi, margini, capacità, inventari, qualità media venduta, investimenti, quote e dividendi.
- Concentrazione per prodotto: HHI calcolato sulle quote di ricavi; `N/D` se nessuna vendita.

Ogni metrica definisce tipo, unità, aggregazione, stock/flusso, frequenza, denominatore, trattamento dei mancanti e versione della definizione in un dizionario dati.
