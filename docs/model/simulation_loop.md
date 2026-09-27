# Ordine settimanale delle operazioni

Documento normativo corrente (revisione 3.2). Riferimenti storici: §10. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 10. Unico ordine dello step settimanale

L'ordine seguente è normativo. Le decisioni possono riferirsi solo a informazioni disponibili nella propria fase; nessuna fase deve essere duplicata in un secondo schema contraddittorio.

| Fase | Operazioni |
|---|---|
| 0. Apertura | Staging transazionale dello stato corrente/RNG (senza ricopiare lo storico), incremento della settimana in lavorazione, applicazione comandi e shock programmati |
| 1. Servizio finanziario | Interessi su stock iniziali di prestiti/depositi/riserve, rinnovo/rientro facilities BC, imposte societarie maturate in `t−1`; obbligazioni non pagate diventano arretrati |
| 2. Tesoro | Stima del fabbisogno, asta titoli con budget privati già disponibili e ordini BC, rimborso dei titoli in scadenza; eventuale arresto economico controllato |
| 3. Piani e credito | Imprese aggiornano prezzi/offerte, piani di produzione/occupazione/investimento; credito per capitale circolante e bisogni primari delle persone usando redditi attesi |
| 4. Lavoro e salari | Licenziamenti programmati, matching, contratti, pagamento di salari/tasse, determinazione del lavoro effettivamente prestato |
| 5. Estrazione | Energia/materiali/metalli prodotti usando lavoro e input disponibili a inizio estrazione; aggiornamento dei giacimenti |
| 6. Risorse | Vendita degli input alle imprese finali e di capitale; ricostituzione scorte delle estrattive per la settimana successiva |
| 7. Produzione | Produzione di beni finali e capitali, consumo degli input, carico degli output a inventario |
| 8. Beni finali | Consumi privati primari → secondari → lusso; acquisti pubblici nella sessione dei prodotti interessati, con regola di priorità dichiarata |
| 9. Investimenti | Aste di nuove quote con budget residui, acquisto di beni capitali finanziati, installazione efficace da `t+1` |
| 10. Chiusura operativa | Deperimento, ammortamento, risultato provvisorio, reputazione, privazioni/arretrati; nessun dividendo prima delle perdite di credito |
| 11. Crisi | Default, liquidazioni/recuperi dovuti, perdite bancarie, risoluzioni; eventuale terminazione controllata |
| 12. Risultati e distribuzioni | Risultati finali dopo perdite/recuperi, imposte maturate e dividendi ammissibili; nel D1 popolazione invariata, punto di estensione demografia D2 |
| 13. Commit | Invarianti, metriche, ledger/eventi e snapshot finali; pubblicazione del nuovo stato e valutazione della pausa |

Nella fase 8, il Governo entra nello stesso matching dei compratori del prodotto secondo una permutazione riproducibile: non ha priorità nascosta sui bisogni primari delle persone. I budget familiari restano separati per livello di bisogno.

Le aste di bond precedono i salari della settimana; quelle azionarie li seguono: è una convenzione temporale esplicita. Entrambi i mercati usano solo cassa già disponibile. La scelta si può raffinare dopo D1, mantenendo test di budget e di sensibilità all'ordine.

Le liquidazioni usano sessioni distinte tracciate; capitale e input acquisiti in liquidazione sono utilizzabili da `t+1`, evitando produzione retroattiva. Gli eventuali arretrati di fase 1 sanati nel corso della settimana non fanno avanzare il contatore di default a fine step.

Le risoluzioni possono propagare perdite ad altre entità, anche attraverso i loro depositi. La fase 11 ripete la rilevazione delle perdite e delle insolvenze fino a stabilizzazione, elaborando ogni procedura una sola volta per entità ed evitando cicli infiniti. Solo le entità sopravvissute e ammissibili distribuiscono dividendi nella fase 12.

Le fasi 1–11 invocano il settlement e, quando serve, il rifinanziamento. Non esiste una fase finale che corregge retroattivamente pagamenti impossibili.
