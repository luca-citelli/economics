# Principi e gerarchia delle regole

Documento normativo corrente (revisione 3.2). Riferimenti storici: §1. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 1. Obiettivo, principi e gerarchia delle specifiche

L'economia deve emergere da decisioni di agenti eterogenei e transazioni verificabili. Inflazione, produzione, occupazione, distribuzione del reddito, credito e debito pubblico sono risultati; non devono essere serie imposte per ottenere grafici plausibili.

Principi obbligatori:

1. **Coerenza fra stock e flussi:** ogni transazione monetaria ha controparti; ogni bene prodotto, consumato o deperito ha una registrazione fisica.
2. **Mercati espliciti:** per ogni bene, servizio, lavoro o attività finanziaria scambiabile esistono regole di offerta, domanda, prezzo, allocazione e regolamento.
3. **Razionamento possibile:** i mercati non devono necessariamente raggiungere l'equilibrio. Possono restare merci invendute, bisogni insoddisfatti, disoccupati, posti vacanti ed emissioni non sottoscritte.
4. **Informazione limitata:** gli agenti prendono decisioni usando il proprio stato e informazioni correnti già disponibili o passate, senza conoscere il futuro.
5. **Riproducibilità:** stessa configurazione, versione del motore, seed e sequenza temporale di comandi economici producono lo stesso risultato, indipendentemente dalla velocità dell'interfaccia.
6. **Separazione dei ruoli:** la banca centrale controlla strumenti monetari; il Governo segue regole fiscali autonome configurate all'avvio.
7. **Ispezionabilità:** ogni indicatore deve permettere di risalire a settori, agenti e transazioni che lo compongono.
8. **Semplicità dichiarata:** ogni semplificazione deve essere esplicita e sostituibile. Gli agenti sono inizialmente regole Python, non LLM; il simulatore non richiede API AI per funzionare.

Nel documento **DEVE** indica un requisito di accettazione; **proposto/default** una scelta implementativa iniziale; **D2/D3** una funzionalità futura. Le parti differite non devono apparire come controlli funzionanti nel D1.

In caso di conflitto, prevalgono perimetro del deliverable, invarianti contabili, ordine dello step e contratti API. L'implementatore registra le ambiguità residue in `DECISIONS.md`, evitando cambiamenti silenziosi delle regole economiche.
