# Imprese e produzione

Documento normativo corrente (revisione 3.2). Riferimenti storici: §7.2. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 7.2 Imprese

Ogni impresa produce un solo prodotto. Campi minimi: ID, prodotto, conto, debiti, quote emesse, lavoratori/contratti, salario offerto, capacità/capitale, inventari separati per input/output, ricetta produttiva, produttività, prezzo offerto, qualità e reputazione, costi medi, ordini/vendite precedenti, stato operativo.

Produzione settimanale:

`q = max(0, min(capacità(K), produttività × lavoratori_effettivi, input_1 / coeff_1, ...))`

Entrano solo input con coefficiente positivo e lavoratori il cui salario può essere pagato. Pagare salari e acquistare input avviene prima della produzione: vietata una liquidità virtuale derivata da vendite future non finanziate.

- Costi degli input e salari sono capitalizzati nel costo della produzione secondo regola dichiarata; unità vendute scaricate al costo medio ponderato.
- Immobilizzazioni si ammortizzano settimanalmente; i nuovi beni capitali acquistati in `t` entrano in capacità in `t+1`.
- Prodotti durevoli hanno scorte, i servizi invenduti scadono a fine settimana; deperimento configurato per prodotto.
- Qualità fissa nel D1; reputazione aggiornata con una media smussata della quota di vendite del prodotto e contenuta in [0,1]. Non usare vendite assolute senza scala, che farebbero divergere il punteggio.
- Profitti contabili e flussi di cassa sono metriche diverse.
- Dividendi, incluse le banche, soltanto da utili distribuibili e liquidità oltre il buffer, senza indebitamento automatico per pagarli.

L'offerta desiderata usa domanda osservata ed evasa/non evasa della settimana precedente, inventario target e capacità. Nessuna impresa conosce gli ordini futuri.
