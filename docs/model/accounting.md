# Contabilità, pagamenti e moneta

Documento normativo corrente (revisione 3.2). Riferimenti storici: §6. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 6. Unità, contabilità e moneta

### 6.1 Convenzioni

- Importi in `UM`; quantità in unità fisiche specifiche del prodotto; lavoro in persone-settimana; salari in `UM/settimana`.
- Prezzi strettamente positivi. Tassi negativi ammessi solo se maggiori di −100% annuo e compatibili con i vincoli del prodotto.
- Tassi annuali effettivi convertiti in settimanali con `r_w = (1 + r_a) ** (1/52) - 1`.
- Stock a fine settimana, flussi della singola settimana; annualizzazioni sempre dichiarate.
- Proposta D1: importi contabili `Decimal`, quantizzati a 0,000001 UM, serializzati come stringhe; quantità fisiche `float64` con tolleranze documentate. Arrotondare a centesimi solo in visualizzazione.
- Residui di riparto attribuiti deterministicamente e registrati, mai corretti alterando saldi senza una scrittura.

### 6.2 Sistema dei pagamenti

Nel D1 non esiste contante fisico: persone e imprese hanno depositi presso banche commerciali; il Governo ha un conto del Tesoro presso la banca centrale; le banche hanno conti di riserva presso la banca centrale.

`cash` e `bank_deposits` non possono essere due copie dello stesso saldo. I saldi derivano dal ledger; eventuali proprietà degli agenti sono viste, non fonti indipendenti modificabili.

| Operazione | Effetto minimo da registrare |
|---|---|
| Prestito bancario di 100 a un'impresa | Banca: +100 prestiti, +100 depositi dovuti; impresa: +100 deposito, +100 debito. Nessuna riserva viene creata dall'erogazione |
| Rimborso del capitale alla propria banca | Riduce deposito e debito del cliente, credito e passività per depositi della banca |
| Pagamento fra clienti della stessa banca | Trasferimento fra depositi; riserve della banca invariate |
| Pagamento fra banche diverse | Trasferimento fra depositi e corrispondente trasferimento di riserve fra le banche |
| Rifinanziamento della banca centrale | Banca: +riserve e +debito verso BC; BC: +credito e +passività per riserve |
| Tassa versata al Tesoro | Riduce deposito privato e riserve della banca; aumenta il conto del Tesoro |
| Spesa pubblica verso un'impresa | Riduce il conto del Tesoro; aumenta riserve della banca ricevente e deposito dell'impresa |
| Acquisto primario di bond da parte della BC | BC: +titolo e +conto del Tesoro; Governo: +conto e +debito. Le riserve private aumentano quando il Tesoro spende |
| Sottoscrizione di quote societarie da una persona | Trasferisce depositi alla società; iscrive quote al sottoscrittore e capitale alla società; non crea moneta di per sé |
| Perdita su un prestito | Riduce il valore del credito e il patrimonio della banca; non cancella automaticamente depositi di terzi |

La scelta fra prestare e detenere attività liquide passa da rischio, rendimento, capitale e regolamento dei pagamenti. **Le banche non prestano riserve direttamente alle persone** e i prestiti non sono limitati da un moltiplicatore monetario fisso.

Ogni pagamento è atomico. Se la banca pagante non ha riserve sufficienti, tenta rifinanziamento nei limiti ammissibili; in mancanza, il pagamento fallisce senza addebitare il cliente o consegnare il bene. Distinguere `insufficient_customer_funds` da `bank_settlement_failure`.

### 6.3 Bilanci e invarianti

Contabilità in partita doppia per ogni entità, collegata da ID di transazione comune. Il ledger registra almeno importo, debitore/creditore contabile, controparti, conto, settimana, fase e causale.

- Ogni entità: attività = passività + patrimonio netto.
- Totale depositi delle persone e imprese = passività per depositi delle banche.
- Riserve delle banche = corrispondenti passività della BC; il conto del Tesoro è separato.
- Ogni prestito e titolo: attività del detentore coerente con passività del debitore, considerate svalutazioni esplicite.
- Emissioni e rimborsi di quote aggiornano insieme registro proprietari e capitale dell'emittente.
- Nessun deposito, riserva disponibile o inventario negativo; eventuale scoperto è un prestito esplicito autorizzato.
- Una garanzia vincolata non può essere impegnata due volte.
- Quantità venduta non superiore all'inventario e spesa non superiore al budget disponibile/vincolato.

Il patrimonio può essere negativo durante la rilevazione di insolvenza; non correggerlo portandolo artificialmente a zero. Inventari e capitale sono valorizzati al costo: acquisto/produzione creano attività, il consumo produttivo e la vendita registrano costi, ammortamento e perdite riducono il patrimonio.

I conti di apertura DEVONO essere coerenti. Un modo ammesso: riserve bancarie iniziali con contropartita esplicita nel bilancio BC; depositi, prestiti, titoli e capitale iniziali costruiti con scritture di apertura; persone proprietarie delle quote iniziali. Non campionare indipendentemente depositi, riserve e capitale sperando che quadrino. Le dotazioni iniziali sono stock ereditati dalla settimana 0, non produzione/reddito della settimana 1.

### 6.4 Aggregati monetari

- `private_deposits`: depositi di persone e imprese non finanziarie.
- `bank_reserves`: riserve bancarie presso BC; nel D1 senza contante coincidono con la base monetaria privata modellata.
- `treasury_balance`: conto del Tesoro, esposto separatamente.
- `central_bank_liabilities`: riserve + conto del Tesoro + eventuali altre passività esplicite.
- Credito privato e debito pubblico sono aggregati distinti dalla moneta.

Non chiamare `M2` una misura priva di tutti i settori/strumenti della definizione statistica reale. Non sommare depositi e riserve sotto un generico «moneta totale».

### Confine con il calcolo vettoriale

La predisposizione NumPy non cambia precisione e autorità del ledger. Array monetari derivati sono solo proiezioni di calcolo; la quantizzazione e la verifica esatta del budget avvengono prima del settlement. Nessuna seconda copia mutabile dei saldi. Dettagli in [performance_and_vectorization.md](../technical/performance_and_vectorization.md), §5.
