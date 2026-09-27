# economics — simulatore economico agent-based

Pacchetto documentale integrato **3.2**, 27 settembre 2026: struttura modulare dell'esempio economics.zip, regole aggiornate della specifica 3.1 e nove schede di implementazione.

L'utente interpreta la banca centrale; mercati e agenti formano prezzi, salari e rendimenti. Webapp locale: motore Python indipendente, FastAPI, React/TypeScript/Vite.

## Stato del progetto

Documentazione completa per iniziare. **Il simulatore non è ancora implementato** e nessun test software/benchmark viene dichiarato superato. Prossimo task: T01. Le cartelle del codice saranno create dai task pertinenti.

## Partire

1. Estrai la cartella `economics` e aprila nel tuo ambiente Claude Code o Codex.
2. Se usi il repository esistente, applica i file come aggiornamento della working tree, mantenendo la tua cronologia e controllando il diff. Lo ZIP documentale non contiene la cronologia Git.
3. Se parti da una nuova cartella, puoi inizializzare Git localmente con `git init`.
4. Incolla il prompt «Primo incarico» di [PROMPTS.md](PROMPTS.md).

Non servono copie della chat o ulteriori documenti. Il lavoro inizia dal task T01; per le continuazioni usare il relativo prompt.

## Documenti

| Percorso | Funzione |
|---|---|
| [SPEC.md](SPEC.md) | Panoramica breve del progetto |
| [docs/INDEX.md](docs/INDEX.md) | Mappa dei documenti per argomento e dei riferimenti storici |
| `docs/model/` | Regole economiche correnti: persone, imprese, lavoro, banche, Governo e mercati |
| `docs/technical/` | Architettura, tempo, API, configurazione, metriche, test |
| [docs/product_scope.md](docs/product_scope.md) | Perimetro dei deliverable |
| [AGENTS.md](AGENTS.md), [CLAUDE.md](CLAUDE.md) | Istruzioni brevi per gli strumenti |
| [docs/CORE_RULES.md](docs/CORE_RULES.md) | Vincoli condivisi |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Stato e prossimo passo |
| [tasks/README.md](tasks/README.md) | Nove task con letture, attività e prove |
| [DECISIONS.md](DECISIONS.md) | Decisioni e dettagli tecnici assegnati |
| [docs/PRODUCT_DECISIONS.md](docs/PRODUCT_DECISIONS.md) | Scelte importanti e default adottati |
| [docs/ACCEPTANCE.md](docs/ACCEPTANCE.md) | Matrice requisiti/evidenze |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | Cosa è stato integrato e corretto |

## Lettura efficiente

A ogni sessione: istruzioni/regole brevi, piano, task corrente e relativi moduli. Non leggere tutta la documentazione. I documenti per argomento contengono le regole; le schede task le applicano senza mantenerne una seconda versione completa. Guida in [docs/READING_GUIDE.md](docs/READING_GUIDE.md).

## Decisioni

Non ci sono decisioni bloccanti per iniziare. Restano i default già proposti: D1 completo in nove task, BC stilizzata con acquisti primari e risoluzione bancaria semplificata. Le alternative e il momento utile per valutarle sono espliciti nel documento delle decisioni di prodotto.

## Installazione del futuro software

Non esistono ancora dipendenze o comandi di lancio dell'app. T01 documenterà Python e test reali, T06 il backend, T07 il frontend, T09 l'installazione locale finale. Non utilizzare il vecchio comando pytest isolato come prova che il progetto sia già implementato.

## Efficienza richiesta

Il progetto prevede già da T01 una struttura adatta a NumPy, non solo una generica promessa di ottimizzazione futura. Dati omogenei per colonne, kernel batch e contabilità separata consentono una migrazione progressiva. Dettagli, precisione e benchmark in [performance_and_vectorization.md](docs/technical/performance_and_vectorization.md).
