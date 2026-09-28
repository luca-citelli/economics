# Banche e credito

Documento normativo corrente (revisione 3.2). Riferimenti storici: §8.5. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 8.5 Credito: prezzo e razionamento

Un contratto registra debitore, banca, capitale, tasso annuale, data di revisione, arretrati, scopo, garanzie e stato. D1: credito rolling con revisione settimanale, interessi sul capitale a inizio settimana e nuovi utilizzi remunerati da quella successiva. Il mancato rinnovo comporta un preavviso/rientro configurato, non cancellazione del debito.

Le banche pubblicano/offrono tassi specifici:

`loan_rate = max(policy_rate + funding_spread, reserve_rate) + operating_spread + expected_loss_rate + capital_premium`

La formula è una regola comportamentale proposta. Probabilità di default e perdita attesa devono avere lo stesso orizzonte annuale del tasso. Il merito creditizio usa redditi/copertura interessi, debito, patrimonio e precedenti arretrati; coefficiente e limiti sono espliciti.

Il cliente considera al massimo K banche, sceglie il minor costo fra offerte ammissibili e accetta una sola erogazione per lo stesso fabbisogno. Erogazioni parziali ammesse se il contratto lo prevede.

Nel D1 le richieste aziendali coprono il circolante e quelle delle persone soltanto l'eventuale
fabbisogno dei tre beni primari. La stima familiare sottrae al costo del paniere primario la
liquidità disponibile e il reddito netto atteso per la settimana; non finanzia bisogni secondari,
lusso o acquisti di titoli. Il reddito atteso usa l'ultima stima netta e, se disponibile, il salario
netto del contratto corrente. Un reddito annuo atteso nullo non sostiene credito.

Il conto del cliente resta presso la banca scelta all'apertura. Se presta una banca diversa, il
credito verso il cliente e il deposito vengono creati insieme e le riserve sono trasferite dalla
banca prestatrice a quella del conto con un unico settlement. L'erogazione interbancaria non può
eccedere le riserve disponibili della banca prestatrice; in caso contrario si concede solo la quota
ammissibile o si registra un rifiuto di liquidità. Interessi e rimborsi di capitale dello stesso
prestito regolano le riserve nella direzione opposta. Nei pagamenti successivi si tenta il
rifinanziamento ammesso; se il settlement fallisce, l'obbligazione resta in arretrato. I parametri
di prezzo T03 sono comuni alle banche, quindi le offerte hanno lo stesso tasso; a parità di tasso
si preferisce la maggiore quota sostenibile e poi la banca del cliente.

Vincoli D1, semplificati e non presentati come normativa vigente:

- limite di leva `equity / total_assets ≥ min_equity_ratio` dopo il nuovo prestito;
- limite di concentrazione sul debitore;
- limiti debito/reddito o copertura del servizio del debito;
- liquidità e garanzie sufficienti per regolare deflussi plausibili;
- rendimento atteso superiore alla soglia di convenienza della banca.

Ogni rifiuto registra il vincolo che ha bloccato il credito. Il credito può essere razionato anche se il richiedente accetta un tasso elevato.

I depositi ricevono un tasso definito dalla politica commerciale della banca, ad esempio `deposit_rate = pass_through × reserve_rate`, con parametri e limiti espliciti. Nel D1 niente trasferimenti speculativi fra banche per inseguire il tasso; la scelta della banca resta quella iniziale salvo risoluzione.
