# Lavoro e salari

Documento normativo corrente (revisione 3.2). Riferimenti storici: §8.4. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 8.4 Lavoro: formazione dei salari

- Le imprese stimano output desiderato e lavoratori necessari, poi pubblicano solo posti compatibili con capitale circolante e limite produttivo.
- Ogni persona ha un salario di riserva. Default: massimo fra un minimo tecnico e il costo atteso dei bisogni primari moltiplicato per un coefficiente; in disoccupazione prolungata può ridursi entro limiti configurati.
- Le imprese modificano il salario offerto in funzione di posti non coperti, candidature e produttività/costi attesi. Il salario aumenta se persistono posti scoperti; non è fissato da una tabella esterna.
- Matching D1 a turni: ogni disoccupato si candida alla migliore offerta ammissibile non ancora tentata; l'impresa accetta fino ai posti disponibili; spareggi casuali riproducibili. Si ripete fino a esaurimento di abbinamenti possibili.
- Salario del nuovo contratto = salario pubblicato e accettato. Contratti esistenti mantengono il salario finché non vengono rinegoziati alle revisioni periodiche configurate; nel D1 niente mobilità volontaria fra imprese occupanti.
- Riduzioni di personale e chiusure liberano i lavoratori; nessun agente lavora per due imprese nello stesso step.
- Il salario lordo è spesa dell'impresa; imposta sul lavoro trattenuta e trasferita al Tesoro, netto accreditato al lavoratore.
- Se il pagamento non è possibile, niente lavoro gratuito: il turno non si svolge, il debito salariale è registrato se contrattualmente maturato e si attiva la procedura di crisi.

Esportare salari offerti, salari dei nuovi contratti, salario medio degli occupati, candidature, posti vacanti e occupazione; la sola media salariale non descrive tutto il mercato.
