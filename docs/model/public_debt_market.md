# Mercato primario del debito pubblico

Documento normativo corrente (revisione 3.2). Riferimenti storici: §8.6. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 8.6 Debito pubblico: asta primaria

D1 usa titoli **zero coupon a 52 settimane**, nominale unitario 1 UM. Nessuna cedola intermedia: il rendimento emerge dal prezzo di emissione e dal rimborso a nominale. Non esiste `government.bond_annual_rate` imposto dall'esterno.

Regola:

1. Il Governo stima fabbisogno di cassa, rimborsi imminenti e buffer. Con il prezzo dell'ultima asta, o un riferimento iniziale esplicito se manca, determina il nominale da offrire.
2. Ogni investitore invia quantità nominale e prezzo massimo, derivato dal rendimento minimo richiesto: `P_max = 1 / (1 + y_min) ** (T/52)`.
3. I rendimenti richiesti dipendono da tassi BC, aspettative adattive sui tassi, rischio sovrano, concentrazione e preferenze. Le persone non acquistano oltre il budget assegnato.
4. Ordinare le offerte per prezzo decrescente. Escludere offerte inferiori al prezzo di riserva dell'emittente, derivato da un rendimento massimo accettato configurabile.
5. Asta a prezzo uniforme: prezzo dell'ultima offerta accettata; allocazione proporzionale fra offerte marginali allo stesso prezzo, con residui deterministici. In sottoscrizione parziale vale il peggior prezzo accettato; zero offerte valide significa zero emissione.
6. Regolare consegna titoli e pagamento al Tesoro. Rendimento di asta calcolato dal prezzo effettivo. Fabbisogno residuo e nominale invenduto sono visibili.

La BC, se abilitata, è un partecipante con un limite di spesa e un prezzo massimo espliciti. La sua partecipazione può influenzare il prezzo, ma non garantisce la copertura del deficit. Nel D1 si tratta di finanziamento monetario primario stilizzato, **non di una replica delle regole della BCE né del QE sul secondario**.

Titoli detenuti a costo ammortizzato nel ledger, con interessi maturati settimanalmente fino al nominale; rendimento/valore indicativo separati. Rimborsi estinguono contemporaneamente attività e passività. Lo stock di debito mostra nominale e valore contabile distintamente. Nessuna liquidabilità automatica prima della scadenza senza mercato secondario.
