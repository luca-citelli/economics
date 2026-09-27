# Interfaccia e ruolo della banca centrale

Documento normativo corrente (revisione 3.2). Riferimenti storici: §4. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 4. Esperienza utente: governatore della banca centrale

### 4.1 Avvio di una simulazione

L'utente sceglie scenario, seed, popolazione, numero di banche e intensità degli shock predefiniti. La schermata distingue:

1. **Configurazione iniziale:** struttura economica, bisogni, tecnologia, fiscalità, regole prudenziali.
2. **Strumenti della banca centrale:** modificabili durante la partita.
3. **Strumenti sperimentali:** shock di energia, produttività o politica fiscale, separati dal ruolo ordinario e chiaramente etichettati.

Una nuova simulazione inizia in pausa alla settimana 0. Non eseguire settimane nascoste. Un eventuale periodo di assestamento è esplicito, numerato e conservato nello storico.

### 4.2 Schermate D1

| Schermata | Contenuti |
|---|---|
| Quadro generale | Settimana, stato, inflazione, produzione reale, disoccupazione, depositi, credito, soddisfazione dei bisogni |
| Banca centrale | Strumenti, valori attivi e programmati, bilancio, riserve, rifinanziamenti, storico decisioni |
| Mercati | Prezzi e volumi per prodotto, domanda finanziabile, domanda insoddisfatta, scorte, salari, tassi e risultati delle aste |
| Banche e finanza | Capitale, liquidità, prestiti, default, rendimenti del debito pubblico, emissioni societarie |
| Agenti | Tabelle filtrabili e dettaglio di persone, imprese e banche con bilanci e transazioni recenti |
| Eventi e scenari | Decisioni, shock, insolvenze, emissioni fallite, avvisi, salvataggio/caricamento ed export |

I grafici mostrano valori effettivi, unità, periodo e metodo di calcolo. I tooltip spiegano in italiano i concetti. Non mostrare un rapporto o un tasso come zero quando è indefinito: usare `N/D`.

I pannelli permettono di osservare le catene di trasmissione senza dichiarare automaticamente causalità: tasso della banca centrale → offerte di credito → finanziamenti → produzione/consumi → prezzi e occupazione. Un confronto causale richiede scenari controllati.

### 4.3 Obiettivi del giocatore

L'esperienza D1 è un laboratorio interattivo, senza vittoria/sconfitta artificiale. L'utente osserva il compromesso fra stabilità dei prezzi, attività reale e stabilità finanziaria. Un obiettivo di inflazione è un riferimento grafico, non una forza che modifica direttamente i prezzi. Il punteggio di gioco è facoltativo e successivo.
