# Persone, preferenze e bisogni

Documento normativo corrente (revisione 3.2). Riferimenti storici: §7.1. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 7.1 Persone

Attributi minimi: ID, età in settimane, stato lavorativo, banca/conto, contratti di prestito, quote/titoli posseduti, propensioni a risparmio/rischio/qualità in [0,1], salario di riserva, redditi attesi, bisogni e soddisfazione.

Nel D1 tutti sono adulti, vivi e appartenenti alla forza lavoro, con al massimo un impiego. L'eventuale proprietario può anche essere dipendente: il possesso di quote non è di per sé lavoro. L'età è registrata ma la demografia è disattivata. Privazione e stress economico sono misurati anche senza mortalità.

Bisogni fisici settimanali:

- Primari uguali per tutti: cibo 10, energia domestica 5, mobilità 3 come valori iniziali proposti.
- Secondari individuali: abbigliamento, intrattenimento, viaggi, estratti all'inizializzazione da normali troncate inferiormente a zero; non ricampionare ogni settimana senza un meccanismo esplicito.
- Lusso senza limite di bisogno, ma con budget finito e utilità marginale decrescente. «Illimitato» non autorizza quantità infinita negli ordini.

Regola D1 del budget, applicata dopo redditi e obbligazioni dovute:

1. Definire liquidità libera, escludendo fondi già vincolati.
2. Riservare un budget per bisogni primari ai prezzi pubblicati; se insufficiente, ripartirlo proporzionalmente al costo dei tre bisogni, evitando che un ordine di iterazione favorisca sempre il cibo.
3. Calcolare risparmio desiderato come quota del reddito netto positivo e buffer di liquidità come multiplo del costo dei primari. È un target, non denaro sottratto al ledger.
4. Usare l'eccedenza per secondari entro i limiti fisici e quindi lusso. Un parametro esplicito di utilizzo del patrimonio, `wealth_drawdown_rate`, consente spesa da risparmi accumulati.
5. Investire soltanto la liquidità rimasta oltre il buffer e il risparmio liquido desiderato; dividere budget fra strumenti con una regola di allocazione normalizzata, non promettere lo stesso denaro a più aste.

Il credito al consumo D1 finanzia carenze dei primari entro limiti di reddito/debito; quello per lusso è D2. Le richieste si basano su redditi attesi osservabili e sono concluse prima di inviare gli ordini finanziati.

La propensione al rischio influenza credito richiesto e investimenti; quella alla qualità influenza il fornitore; quella al risparmio il buffer e il consumo. Ogni utilizzo deve essere documentato in una funzione di decisione separata.
