# Specifica del simulatore — panoramica

**Revisione integrata 3.2 — 27 settembre 2026.** Il modello completo è descritto nei moduli normativi elencati in [docs/INDEX.md](docs/INDEX.md). Questo file è una panoramica: non esiste una seconda specifica corrente monolitica da mantenere.

## Obiettivo

Una webapp locale in cui l'utente interpreta la banca centrale di un'economia chiusa: un Governo autonomo, una BC, una valuta, molte persone, imprese e banche. Il motore Python è indipendente; FastAPI lo collega al frontend React/TypeScript/Vite.

Ogni step è una settimana. L'utente controlla pausa, +1, +N e velocità automatica; le decisioni monetarie si applicano a confini di step dichiarati. Prezzi, salari, credito e rendimenti derivano da mercati espliciti e transazioni contabili/fisiche coerenti.

## Dove trovare i requisiti

- [Perimetro D0/D1/D2/D3](docs/product_scope.md).
- [Indice completo dei moduli](docs/INDEX.md).
- [Vincoli comuni](docs/CORE_RULES.md).
- [Piano e stato](IMPLEMENTATION_PLAN.md), [nove task](tasks/README.md) e [accettazione](docs/ACCEPTANCE.md).
- [Default delle decisioni di prodotto](docs/PRODUCT_DECISIONS.md) e [decisioni tecniche](DECISIONS.md).
- [Come iniziare](PROMPTS.md).

D1 include interfaccia, mercati, banche, fiscalità, investimenti, crisi, metriche e checkpoint. Demografia completa, nuove imprese, zecca e mercati secondari sono successivi. I dettagli sono nel documento di perimetro, che è la fonte autorevole per questa distinzione.

## Precedenza e manutenzione

I moduli correnti sono normativi; le schede task indicano lavoro e verifiche; i riepiloghi servono all'orientamento. Una contraddizione va risolta aggiornando i documenti interessati, non scegliendo silenziosamente una regola. Le decisioni approvate che cambiano il modello vanno riflesse nei moduli e nei task.

I numeri §1–§17 presenti nei moduli sono riferimenti ereditati dalla 3.1 e instradati dall'indice; non rimandano a sezioni mancanti di questo file. La v2 in archivio è storica. Nessuna modifica economica di perimetro è stata introdotta dall'integrazione 3.2.

## Requisito aggiunto: efficienza NumPy

Il motore è predisposto dal T01 a stato per colonne e kernel numerici NumPy, con percorso ibrido che mantiene settlement e contabilità esatta. Specifica in [performance_and_vectorization.md](docs/technical/performance_and_vectorization.md). Questo requisito tecnico aggiunto dal proprietario non cambia l'economia dei mercati.
