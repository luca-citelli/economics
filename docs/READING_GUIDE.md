# Lettura mirata dei documenti

## Percorso ordinario

1. Istruzioni in [AGENTS.md](../AGENTS.md), richiamate da CLAUDE.md.
2. [CORE_RULES.md](CORE_RULES.md), [piano](../IMPLEMENTATION_PLAN.md) e task corrente.
3. Moduli elencati nella sezione «Letture mirate» della scheda, poi decisioni pertinenti.
4. [INDEX.md](INDEX.md) per scoprire altre dipendenze.

SPEC.md è una panoramica breve. Non contiene il modello completo; le regole correnti sono direttamente nei file per argomento. Non servono estrazioni per numeri di riga da una specifica monolitica.

## Obbligatorio e condizionale

Ogni task distingue moduli da leggere e documenti da consultare per le sole parti interessate. All'interno di un modulo lungo (ad esempio metriche o tempo), usare titoli o ricerca testuale per leggere il sottoparagrafo necessario. Non è richiesto rileggere moduli invariati già presenti nel contesto della stessa sessione.

Le contropartite contabili e i contratti pubblici richiedono talvolta letture trasversali: modificare un prestito richiede verificare il conto del debitore e della banca; cambiare un comando coinvolge runner e UI. Non usare la lettura selettiva come pretesto per ignorare questi legami.

## Riferimenti storici

I numeri § ereditati dalla 3.1 sono conservati nei titoli dei moduli. L'indice li mappa a percorsi reali. Per esempio §8.6 è public_debt_market.md e §10 è simulation_loop.md. Essi non rimandano a sezioni mancanti di SPEC.md.

## Fonte unica e archivio

Una regola dettagliata ha una sola sede normativa. CORE_RULES e le schede sono riepiloghi/istruzioni e si aggiornano insieme al modulo se cambia la regola. Un'eventuale raccolta completa futura deve essere generata dai moduli e dichiarata non modificabile direttamente, mai mantenuta a mano come seconda fonte.

L'archivio v2 è esclusivamente storico. Tutti i documenti necessari allo sviluppo ordinario sono presenti; se emergono lacune nuove, registrarle e risolverle, non recuperare implicitamente una vecchia regola superata.

## Fine sessione

Piano breve con risultato, verifiche realmente eseguite, problemi e prossimo passo; decisioni durevoli nel registro; report lunghi collegati quando creati. Una nuova sessione può così riprendere senza rileggere la chat o l'intera documentazione.
