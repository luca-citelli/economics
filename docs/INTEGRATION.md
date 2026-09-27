# Integrazione 3.2 — contenuti e correzioni

27 settembre 2026. Fonti: pacchetto documentale 3.1 e esempio economics.zip. Entrambi contenevano documentazione; nessun codice del simulatore viene perso o dichiarato già realizzato.

## Cosa è stato mantenuto

- Dall'esempio: nome economics, organizzazione docs/model e docs/technical, indice per argomento e archivio originale v2.
- Dalla 3.1: regole economiche/tecniche aggiornate, nove task, piano, decisioni, matrice di accettazione e prompt per i due strumenti.
- Perimetro: webapp locale, una economia, strumenti monetari, mercati espliciti, contabilità, tempo controllabile e milestone D1/D2/D3.

## Correzioni effettuate

- Popolati i documenti operativi mancanti; ogni voce dell'indice rimanda a un file esistente.
- SPEC ridotto a panoramica; regole dettagliate trasferite ai moduli senza una seconda specifica corrente duplicata.
- Sostituiti i due vecchi estratti attivi (banca centrale e ciclo) con le regole aggiornate; il vecchio ciclo non rimane in concorrenza con quello normativo.
- Riscritti indice e CLAUDE, eliminati blocchi Markdown non chiusi e testo da esempio. CLAUDE rimanda alle istruzioni condivise AGENTS.
- Collegate le nove schede a letture obbligatorie/condizionali per argomento; rimossi i prompt che chiedevano di estrarre sezioni da SPEC monolitico.
- Conservato full_spec_v2.md invariato, con avviso separato di archivio storico. Il divieto di usarlo normalmente non impedisce più di accedere alle regole correnti.
- Reso esplicito che non esistono ancora software eseguibile, dipendenze installate o test superati.
- Documentati default di prodotto e dettagli tecnici assegnati ai task; nessuna nuova conferma necessaria per iniziare.

## Continuità dei requisiti economici

Le sezioni economiche/tecniche della 3.1 sono state trasferite nei moduli mantenendo il testo delle regole. La struttura del repository e il workflow sono adattati alla nuova organizzazione. Nessun mercato, vincolo contabile o requisito D1 è eliminato nell'integrazione.

Le differenze rispetto alla v2 (interfaccia, tempo, moneta, crisi, aste, metriche e demografia differita) restano quelle già introdotte nella revisione precedente. L'archivio non reintroduce zecca, nuove imprese e demografia nel D1.

## Applicazione al repository esistente

Usare questo pacchetto come aggiornamento documentale della working tree. Mantenere la cronologia Git del proprio checkout e controllare il diff prima di committare; l'archivio distribuito non include configurazione o cronologia Git. I vecchi documenti attivi omonimi sono sostituiti dalle versioni integrate.

## Verifiche del pacchetto

Controllare link relativi, bilanciamento dei blocchi Markdown, copertura dei task, unicità e copertura delle regole trasferite, presenza delle voci del vecchio indice e integrità dello ZIP. Queste sono verifiche documentali, non prove software o di validazione macroeconomica.

## Richiesta successiva incorporata: NumPy

Il proprietario ha richiesto esplicitamente efficienza e predisposizione al calcolo vettoriale durante l'integrazione. Aggiunto il modulo performance_and_vectorization, aggiornati architettura, task, invarianti, piano e accettazione. Unica estensione tecnica alla 3.1: layout numerico dal T01, kernel progressivi, memoria/RNG/precisione e benchmark di scala. Nessuna nuova regola economica.
