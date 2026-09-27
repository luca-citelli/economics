# Istruzioni operative del repository

Leggi [docs/CORE_RULES.md](docs/CORE_RULES.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) e la scheda del task corrente in `tasks/`. Apri i moduli normativi collegati da quella scheda e le decisioni pertinenti in [DECISIONS.md](DECISIONS.md). [docs/INDEX.md](docs/INDEX.md) è la mappa per trovare altre dipendenze.

`SPEC.md` è una panoramica breve, non una specifica monolitica. Le regole correnti hanno una sola sede per argomento in `docs/model/`, `docs/technical/` e `docs/product_scope.md`. L'archivio v2 è storico e non guida lo sviluppo ordinario. Non caricare tutti i moduli o task a ogni sessione; amplia la lettura se tocchi altre contropartite/contratti.

Implementa solo il task assegnato, salvo autorizzazione a proseguire attraverso più milestone. Le scelte tecniche ordinarie sono autonome e vanno registrate. I default in [docs/PRODUCT_DECISIONS.md](docs/PRODUCT_DECISIONS.md) non richiedono nuova conferma; chiedi solo per un cambiamento sostanziale o un blocco reale.

Stato iniziale: documentazione pronta, nessun simulatore implementato. Non inventare codice preesistente, test eseguiti o prestazioni. Documenta nel README i comandi reali man mano che il progetto diventa eseguibile.

A fine task: verifica pertinente, piano e matrice di accettazione aggiornati, decisioni nuove registrate, risultato/limiti/prossimo passo. Conserva i cambiamenti dell'utente. Se Git è disponibile, usa checkpoint locali; nessun push o deploy è compreso nel D1.
