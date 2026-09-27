# Test, scenari e completamento

Documento normativo corrente (revisione 3.2). Riferimenti storici: §14. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 14. Scenari, verifiche e criteri di accettazione

### 14.1 Test contabili e fisici obbligatori

1. Prestito di 100: +100 depositi e credito; riserve invariate alla creazione. Rimborso di 40: riduzione coerente di capitale e depositi.
2. Pagamento intra/interbancario: importi preservati e riserve trasferite solo nel secondo caso; settlement fallito non modifica metà della transazione.
3. Tasse/spesa e acquisti primari BC: riconciliazione di conto Tesoro, riserve, depositi e titoli.
4. Interessi con tasso zero, positivo e negativo; nuovi prestiti non remunerati retroattivamente.
5. Nessuna produzione senza lavoro/input/capitale; quantità consumate, deperite e residue riconciliate.
6. Default e svalutazioni riducono il patrimonio della corretta controparte; liquidazioni senza compratori non creano recuperi di cassa.
7. Conversione depositi in quote: depositor asset, bank liability ed equity riconciliati; nessuna creazione di riserve.
8. Aste con offerte insufficienti, pareggi, budget limitati, zero domanda, prezzo marginale, raccolta minima non raggiunta e maturità dei titoli.
9. Sottoscrizioni societarie: denaro trasferito, quote emesse, diluizione e dividendi corretti.
10. Distinzione prezzi offerti/transati; settimana senza vendite, CPI con imputazioni e anno non ancora disponibile.

Questi test verificano identità e casi limite; non devono essere semplici copie della formula implementata.

### 14.2 Test del tempo e dell'applicazione

- Stesso seed e comandi alle stesse settimane: risultati economici identici in manuale, batch e automatico a velocità diverse.
- Confronto 100 step continui con 40 step + salvataggio/caricamento + 60 step: stesso checksum economico, escludendo ID del nuovo run e metadati di esecuzione.
- Comando duplicato, richieste simultanee, pausa durante uno step, velocità cambiata mentre si esegue, riconnessione WebSocket: nessun doppio step o aggiornamento parziale.
- Un errore iniettato a metà step lascia il checkpoint precedente invariato e rende visibile `ERROR`.
- Un default sovrano previsto produce `TERMINATED`, evento economico e bilanci coerenti.
- Percorso browser: avvio → +1 → modifica tasso dalla prossima settimana disponibile → avvia → cambia velocità → pausa → salva → ricarica → export.
- Una build frontend per produzione è realmente servibile dal backend locale.

### 14.3 Scenari minimi D1

| Scenario | Intervento | Verifica |
|---|---|---|
| Base | Nessuno shock | 260 settimane con dati finiti, invarianti rispettate, attività e occupazione non collassate per errori di inizializzazione |
| Rialzo tassi | +200 punti base ai tassi rilevanti dalla settimana 53 | Corretta applicazione e trasmissione ai nuovi contratti; osservazione degli effetti aggregati |
| Shock energia | −30% capacità estrattiva per 13 settimane | Rispetto del vincolo fisico, quantità razionate e successivo ripristino; prezzi emergenti |
| Stretta creditizia | Riduzione dell'appetito al rischio delle banche come shock di scenario | Aumento dei rifiuti nei casi costruiti; motivi tracciabili |
| Acquisti BC | Ordini all'asta pubblica con budget finito | Solo scambi eseguiti modificano i bilanci; fabbisogno residuo esposto |
| Asta fallita | Domanda insufficiente per il debito | Spesa razionata o evento di default senza saldo Tesoro inventato |
| Crisi bancaria | Perdite su crediti controllate | Separazione liquidità/solvibilità, risoluzione e perdite coerenti |
| Investimento | Impresa profittevole offre nuove quote | Raccolta, diluizione, acquisto capitale, capacità aumentata da `t+1` |

Gli effetti macroeconomici non sono garantiti monotonicamente: un rialzo dei tassi non deve essere programmato per ridurre sempre inflazione o credito. Testare direttamente la trasmissione nelle condizioni costruite; esaminare gli esiti macro su più seed con statistiche e grafici.

Dopo i test meccanici, eseguire almeno 5 seed per gli scenari principali e riportare mediana/intervallo degli esiti. Divergenze e collassi possono essere risultati del modello; devono essere diagnosticati e distinti da errori, non eliminati forzando le metriche.

### 14.4 Completamento D1

D1 è completo solo quando:

- Tutte le righe della tabella §2.3 hanno un'implementazione e un'evidenza di verifica.
- Una nuova installazione segue il README e apre la webapp locale senza interventi manuali sul codice.
- Configurazioni, scenari, metriche e checkpoint hanno schemi documentati.
- Dashboard e mercati leggono il medesimo stato del motore; nessun dato finto nei percorsi accettati.
- Baseline da 1.000 persone, 3 banche e 3 imprese per prodotto: report di 260 settimane, tempo totale, tempo mediano/p95 per step e memoria, con macchina e versioni specificate.
- Target iniziale indicativo: 1 step/secondo e comandi percepiti come reattivi sulla macchina di riferimento; misurare prima di promettere 10 step/secondo.
- Nessun errore silenzioso, conto sbilanciato o feature differita rappresentata come funzionante.
- Sono documentati limiti economici, risultati non intuitivi e problemi aperti.

Il passaggio dei test software dimostra coerenza implementativa, non validazione empirica dell'economia simulata.

## Verifiche aggiuntive di efficienza

Applicare [performance_and_vectorization.md](performance_and_vectorization.md): equivalenza dei kernel scalari/vettoriali, precisione al confine con il ledger, RNG, gestione delle viste e rollback. T08 misura profiling per fase e benchmark di scala 10.000 persone/52 settimane oltre alla baseline 1.000/260. Non è promesso un throughput minimo alla scala maggiore; sono obbligatori misurazione/diagnosi e coerenza, non un risultato economico predeterminato.
