# Perimetro e deliverable

Documento normativo corrente (revisione 3.2). Riferimenti storici: §2. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](INDEX.md).

## 2. Perimetro e deliverable

### 2.1 Economia iniziale

- Economia chiusa: un Governo, una banca centrale, una valuta astratta `UM`.
- Nessun commercio estero, cambio o trasferimento da un settore estero implicito.
- Persone eterogenee, imprese concorrenti, più banche commerciali.
- Sette prodotti finali: cibo, energia domestica, mobilità, abbigliamento, intrattenimento, viaggi, lusso aggregato.
- Tre risorse intermedie: energia all'ingrosso, materiali, metalli preziosi.
- Un bene capitale aggregato, acquistabile dalle imprese per espandere la capacità.
- Energia all'ingrosso ed energia domestica sono prodotti distinti: la seconda richiede trasformazione/distribuzione.
- I metalli preziosi entrano almeno nella produzione del lusso anche nel regime fiat, così da avere domanda reale prima dell'introduzione della zecca.

### 2.2 D0 — Fondamenta eseguibili

D0 è una milestone tecnica interna: motore Python, contabilità, configurazione validata, inizializzazione coerente, CLI e test essenziali. Non è ancora il primo deliverable per l'utente.

### 2.3 D1 — Primo deliverable interattivo

D1 DEVE comprendere:

| Area | Requisito |
|---|---|
| Esperienza | Webapp locale desktop, dashboard e pannello banca centrale |
| Tempo | Pausa, +1 settimana, +N settimane, esecuzione continua e velocità configurabili |
| Agenti | Persone adulte, imprese finali/estrattive/beni capitali, banche, un Governo, una banca centrale |
| Popolazione | Dimensione iniziale configurabile; popolazione costante nel D1 |
| Bisogni | Primari prioritari, secondari eterogenei, lusso senza tetto fisico ma con budget finito |
| Produzione | Vincoli di lavoro, capitale, risorse, inventari e capacità di pagamento |
| Mercati | Tre gruppi di beni finali, risorse, beni capitali, lavoro, credito, debito pubblico, capitale di rischio primario |
| Moneta | Depositi e riserve distinti; credito bancario con contropartite contabili |
| Politica monetaria | Tasso sulle riserve, tasso di rifinanziamento, liquidità d'emergenza e acquisti primari di titoli secondo le regole descritte sotto |
| Governo | Tasse proporzionali, acquisti pubblici, emissioni, interessi e rimborso del debito |
| Investimenti | Sottoscrizione di titoli pubblici e nuove quote di imprese esistenti; acquisto di beni capitali |
| Crisi | Default imprese, perdite bancarie, distinzione liquidità/solvibilità, risoluzione bancaria semplificata |
| Dati | Metriche settimanali, eventi, export CSV, salvataggio e ripresa deterministica |
| Validazione | Test di transazioni, mercati, runner, API e percorso utente; scenario base eseguibile per 260 settimane |

Il D1 è già un progetto di dimensioni significative. La riduzione riguarda demografia e regimi alternativi, non l'eliminazione dei mercati richiesti.

### 2.4 D2 — Estensione della dinamica degli agenti

- Nascite, invecchiamento, morte naturale e morte per privazione persistente.
- Nuclei familiari, mantenimento dei minori e successione patrimoniale semplice ma contabile.
- Fondazione di nuove imprese e scelta fra lavoro dipendente e imprenditoria.
- Credito al consumo non essenziale e all'imprenditoria più articolato.
- Cambi di lavoro, negoziazione dei contratti esistenti e competenze differenziate.
- Confronto affiancato di scenari e diramazione di un salvataggio per provare politiche diverse.
- Ricapitalizzazione pubblica delle banche distinta dai prestiti della banca centrale.

### 2.5 D3 — Regimi e mercati avanzati

- Regime zecca/metalli, regole di convertibilità e vincoli al credito coerenti con quel regime.
- Mercati secondari per titoli e quote, acquisti/vendite della banca centrale sul secondario.
- Mercato interbancario, titoli a diverse scadenze, ammortamento del credito.
- Qualità e tecnologia endogene, scoperta di risorse, pensioni, immobiliare.
- Eventuali economia aperta, più Stati e valute solo in un'estensione successiva.

Restano fuori dal D1 anche derivati, modelli ML, database distribuiti, multiplayer e implementazione di normative bancarie reali complete.
