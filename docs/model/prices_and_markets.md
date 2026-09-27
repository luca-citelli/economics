# Contratti, mercati e prezzi dei beni

Documento normativo corrente (revisione 3.2). Riferimenti storici: §8.1–8.3. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 8.1 Contratto comune

Ogni mercato ha ID, prodotto/strumento, partecipanti ammessi, unità, calendario, regola di prezzo, regola di matching, priorità, vincoli di budget/inventario, criteri di spareggio e metriche.

Oggetti minimi:

- `Offer`: venditore, prodotto, quantità, prezzo, qualità, settimana.
- `Order/Bid`: compratore, quantità/budget, prezzo massimo o rendimento minimo, settimana.
- `Trade`: ID, acquirente, venditore, quantità, prezzo, costo totale, riferimenti al pagamento e allo strumento.
- `MarketResult`: offerte, domanda finanziabile, transazioni, domanda non eseguita, offerta residua, prezzi e motivi di mancata esecuzione.

La funzione di mercato produce transazioni; il settlement le esegue atomicamente. Un'offerta non equivale a una vendita. Gli ordini D1 scadono a fine sessione e liberano i budget vincolati. Fra fasi diverse lo stesso deposito non può essere impegnato due volte.

### 8.2 Mappa completa

| Mercato | Offerta | Domanda | Prezzo |
|---|---|---|---|
| Beni primari | Imprese di cibo, energia domestica, mobilità | Persone, acquisti pubblici ammessi | Prezzi offerti distinti per prodotto e impresa |
| Beni secondari | Abbigliamento, intrattenimento, viaggi | Persone/Governo | Prezzi offerti distinti |
| Lusso | Imprese del lusso aggregato | Persone | Prezzi offerti e scelta per qualità/reputazione |
| Risorse | Estrattive | Imprese produttive ed estrattive per scorte future | Prezzi per energia, materiali, metalli |
| Beni capitali | Produttori di capitale | Imprese che investono | Prezzi per unità di capitale |
| Lavoro | Persone disponibili | Imprese con posti vacanti finanziabili | Salario concordato nei contratti |
| Credito | Banche | Persone e imprese | Tasso offerto per rischio, condizioni e disponibilità |
| Debito pubblico primario | Governo emittente | Persone, banche, BC se abilitata | Asta prezzo/rendimento |
| Capitale di rischio primario | Imprese esistenti emittenti | Persone investitrici | Asta per nuove quote |

Primari e secondari sono famiglie di mercati, non due beni perfettamente sostituibili. Non deve esistere un unico prezzo al quale cibo e mobilità diventano indistinguibili.

Il mercato dei capitali comprende qui debito pubblico e quote societarie; il credito è un canale distinto. L'investimento finanziario nelle quote e l'investimento reale in macchinari sono operazioni diverse, collegate dal budget dell'impresa.

### 8.3 Beni finali, risorse e capitale: prezzi offerti e matching

Non è necessario un order book continuo. D1 usa prezzi offerti dalle imprese, aggiornati prima della sessione usando dati passati.

Regola proposta, parametrica e testabile:

`p_t = max(p_floor, p_(t-1) × exp(clip(a × excess_demand_signal + b × cost_gap, -g, +g)))`

`excess_demand_signal = (unfilled_demand_(t-1) - excess_inventory_(t-1)) / max(expected_sales_(t-1), epsilon)`; `cost_gap` confronta prezzo e costo medio maggiorato del markup target. Le scale, `a`, `b`, `g` e la finestra dei costi sono in configurazione.

`p_floor` è un minimo tecnico positivo, non un divieto universale di vendere sotto costo. Consentire sconti e liquidazioni; prezzi sotto costo persistenti peggiorano i conti. «Aggiornato ogni settimana» significa ricalcolato: un prezzo può restare invariato.

Procedura di acquisto:

1. Il venditore pubblica prezzo, quantità e caratteristiche; non vende produzione non ancora disponibile.
2. Ogni compratore definisce budget e quantità massima; per beni essenziali viene prima la soddisfazione fisica.
3. Classifica i venditori con un punteggio senza unità: prezzo relativo al prezzo di riferimento del prodotto, qualità e reputazione normalizzate. Coefficiente sul prezzo negativo.
4. I compratori sono elaborati in una permutazione riproducibile ogni settimana; quelli razionati tentano il fornitore successivo fino a esaurimento del budget, del bisogno o delle offerte.
5. Esecuzione al prezzo offerto, pagamento e consegna atomici; registrazione della domanda non evasa senza duplicare la stessa domanda nei tentativi successivi.

L'ordine casuale evita un privilegio permanente degli ID bassi, ma introduce razionamento sequenziale: documentarlo come semplificazione D1. Domanda desiderata non finanziabile e ordini finanziabili non eseguiti sono due misure separate.
