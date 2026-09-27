# Prompt operativi

Questi prompt fanno riferimento ai file di questo repository. Il piano e le schede sono già preparati: aggiornarli, non riscriverli da zero senza motivo.

## Primo incarico — T01

```text
Apri questo repository e segui AGENTS.md (e CLAUDE.md se pertinente).
Leggi docs/CORE_RULES.md, IMPLEMENTATION_PLAN.md e tasks/T01.md.
Consulta DECISIONS.md e i moduli normativi collegati da T01.
Usa docs/INDEX.md per altre dipendenze. SPEC.md è solo una panoramica;
non caricare tutti i moduli o l’archivio v2 per default.

Il progetto è ancora documentale: implementa T01, dalla configurazione
e contabilità fino all'inizializzazione coerente e ai test richiesti.
Conserva perimetro D1 e scelte già prese. Predisponi subito lo stato
per colonne e i kernel NumPy secondo il modulo performance; ledger separato. Definisci autonomamente i dettagli
tecnici ordinari e registrali; segnala solo ambiguità sostanziali.
Non implementare T02–T09 in questo incarico.

Esegui le verifiche pertinenti, correggi i problemi, aggiorna piano,
decisioni e matrice di accettazione. Riporta cosa funziona, comandi realmente
eseguiti, risultati, limiti e prossimo passo. Non fermarti alla pianificazione.
```

## Prosecuzione — task successivo

```text
Segui AGENTS.md. Leggi docs/CORE_RULES.md e IMPLEMENTATION_PLAN.md.
Individua il primo task non completato con dipendenze soddisfatte e leggi
la sua scheda in tasks/. Consulta solo decisioni e moduli collegati pertinenti;
amplia la lettura se scopri dipendenze o ambiguità.

Verifica il codice esistente, poi implementa quel task fino ai criteri d'uscita.
Non ricreare il progetto e non sostituire con mock componenti già implementati.
Esegui le verifiche necessarie e aggiorna piano, decisioni e accettazione.
Riporta evidenze, limiti e prossimo passo. Ferma l'incarico a fine task.
```

## Ripresa dopo interruzione

```text
Segui AGENTS.md e leggi il riepilogo corrente in IMPLEMENTATION_PLAN.md.
Controlla lo stato reale dei file e, se presente, Git: il piano può essere
stato scritto prima dell'ultima modifica. Riprendi il task in corso dalla sua
scheda, consultando solo i moduli pertinenti.
Non ricominciare da zero e non ripetere verifiche già documentate salvo che
cambiamenti o rischi concreti lo richiedano. Completa e verifica il task.
```

## Revisione economica dopo T01, T04 o T05

```text
Revisiona la milestone appena completata rispetto alla sua scheda,
docs/CORE_RULES.md e ai moduli normativi pertinenti.
Controlla contropartite, inventari, budget, ordine temporale e perdite.
Cerca casi in cui il risultato sembra plausibile ma viola un'identità.
Correggi errori implementativi nello scope corrente e aggiungi test mirati.
Non cambiare le regole economiche per far passare i test: segnala un'eventuale
contraddizione sostanziale e registra le evidenze nel piano.
```

## Incarico autonomo fino a D1

```text
Segui AGENTS.md, docs/CORE_RULES.md e IMPLEMENTATION_PLAN.md.
Sei autorizzato a procedere attraverso T01–T09 fino al completamento di D1.
Leggi una scheda alla volta e i suoi moduli; non caricare tutte le schede
e tutti i documenti a ogni fase. Rispetta dipendenze e criteri d'uscita.
Aggiorna i file di stato e conserva checkpoint locali dopo ogni milestone.
Esegui le revisioni economiche dopo T01, T04 e T05 come verifiche interne.
Procedi senza chiedere conferma per scelte ordinarie già coperte dai documenti.
Fermati solo per un blocco reale o una decisione che cambi materialmente
perimetro/regole economiche. Non includere D2/D3 o pubblicazione online.
```

## Passaggio fra Claude Code e Codex

```text
Il lavoro è iniziato con un altro strumento. La fonte di verità è questo
repository, non il ricordo di una chat. Segui AGENTS.md e riprendi da
IMPLEMENTATION_PLAN.md, verificando il codice e le evidenze esistenti.
Usa la stessa specifica, gli stessi criteri e le stesse decisioni.
Non duplicare o migrare il progetto per adattarlo al tuo strumento.
```
