# Crisi, liquidazioni e risoluzione bancaria

Documento normativo corrente (revisione 3.2). Riferimenti storici: §9.3. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 9.3 Liquidità, insolvenza e risoluzione

Tre situazioni distinte:

- **Impresa illiquida:** pagamenti non eseguiti, tentativo di credito, sospensione delle attività non finanziate.
- **Banca illiquida ma solvente:** tentativo di rifinanziamento garantito; nessuna perdita cancellata.
- **Banca insolvente:** patrimonio negativo dopo perdite; un prestito BC aggiunge attività e passività per lo stesso importo e non risolve il deficit patrimoniale. Patrimonio positivo ma sotto il requisito indica sottocapitalizzazione: blocco del nuovo credito e dei dividendi, non insolvenza automatica.

Default di imprese/persone dopo `arrears_grace_weeks` consecutive di obbligazioni non pagate; default immediato se un trigger patrimoniale esplicito lo prevede. Arretrati e interessi sospesi sono registrati, senza creazione di depositi fittizi. Le imprese in crisi non assumono né distribuiscono dividendi.

Liquidazione D1: prima cassa disponibile, poi inventari/capitale messi sul rispettivo mercato con sconto. Solo vendite eseguite generano recuperi; realizzi non avvenuti entro il termine vengono svalutati a zero con scrittura. Creditori pagati secondo priorità configurata (salari/imposte, crediti garantiti entro garanzia, residuo chirografario pro rata); soci ultimi. Una garanzia ceduta in natura è uno scambio contabile esplicito, non cassa inventata.

**Risoluzione bancaria minima D1:** azzeramento delle quote dei vecchi azionisti e conversione pro rata di depositi non garantiti in nuove quote per assorbire il deficit e ricostituire un capitale target. Con patrimonio iniziale `E < 0` e target `E_target > 0`, i depositi da convertire sono `H = E_target - E`, entro i depositi disponibili. Nel bilancio della banca la riduzione di passività H assorbe il deficit e porta il patrimonio a E_target. Ai depositanti si attribuiscono tutte le nuove quote pro rata, valorizzate complessivamente a E_target ai fini del modello: la differenza `H - E_target` è una perdita, non un'attività recuperata. Registrare la perdita anche sui portafogli dei vecchi azionisti. Il valore economico delle nuove quote può comunque differire da quello contabile. Attività e contratti di prestito restano in un successore tracciato; il fallimento della banca non cancella il debito dei clienti.

La conversione non crea riserve. Dopo ricapitalizzazione la banca deve ancora superare il controllo di liquidità. Se la conversione possibile è insufficiente o non esiste accesso a liquidità per riprendere i pagamenti, il D1 termina con evento di crisi bancaria non risolta e stato contabile integro. Niente assicurazione implicita dei depositi.

**D2:** ricapitalizzazione a carico del Governo mediante acquisto di quote, finanziata da cassa/debito, se lo scenario la abilita. Un trasferimento gratuito BC a una banca è un sussidio con perdita/variazione patrimoniale BC, diverso da rifinanziamento e acquisto di asset: è escluso dal D1 e va etichettato esplicitamente se aggiunto.
