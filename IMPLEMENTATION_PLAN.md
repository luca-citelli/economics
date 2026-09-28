# Piano di implementazione D1

Aggiornamento: 28 settembre 2026. **T05 completato e verificato**: economia integrata da CLI con quote primarie, investimento reale, default, liquidazioni e risoluzioni bancarie. D1 richiede ancora runner/API, frontend, calibrazione e consegna.

## Ripresa rapida

- Task corrente: nessuno; T05 chiuso.
- Prossimo task: **T06**, da avviare su incarico.
- Ultimo risultato: package 0.5.0; profilo `complete_economy` e tre scenari CLI investimento/crisi.
- Codice esistente: `src/economic_sim/`, `configs/`, `tests/`; checkpoint locale T05 `1ecb7a2`.
- Verifiche eseguite: 125 test, Ruff, lock, build 0.5.0 e quattro run CLI da 52 settimane con invarianti; [report T05](docs/reports/T05.md).
- Problema economico aperto: nel run base T05 l'occupazione scende a 38 e la soddisfazione primaria a zero alla settimana 52. La raccolta azionaria non si attiva nel profilo base, ma funziona nello scenario investimento. Calibrazione/diagnosi macro resta T08.
- Prima azione successiva: leggere T06 e i moduli collegati; preservare vincoli, controparti, eventi e test T01–T05.

## Stato delle milestone

| ID | Task | Dipendenze | Stato | Evidenza di completamento |
|---|---|---|---|---|
| T01 | [Contratti e inizializzazione](tasks/T01.md) | Nessuna | DONE | [Report](docs/reports/T01.md): 52 test, Ruff, build, CLI e wheel verificati; `26986e7` |
| T02 | [Economia reale](tasks/T02.md) | T01 | DONE | [Report](docs/reports/T02.md): 86 test, Ruff, build, 52 settimane/CSV e invarianti; `210063a` |
| T03 | [Banche e politica monetaria](tasks/T03.md) | T01–T02 | DONE | Follow-up credito familiare/cross-bank; 109 test, run T03 52 settimane; [Report](docs/reports/T03.md) |
| T04 | [Governo e debito](tasks/T04.md) | T03 | DONE | [Report](docs/reports/T04.md) |
| T05 | [Capitale e crisi](tasks/T05.md) | T02–T04 | DONE | [Report](docs/reports/T05.md): 125 test, Ruff, build, quattro run CLI/52 settimane; `1ecb7a2` |
| T06 | [Runner e API](tasks/T06.md) | T01–T05 | NOT_STARTED | Non ancora implementato |
| T07 | [Frontend interattivo](tasks/T07.md) | T06 | NOT_STARTED | Non ancora implementato |
| T08 | [Calibrazione e robustezza](tasks/T08.md) | T01–T07 | NOT_STARTED | Non ancora implementato |
| T09 | [Consegna](tasks/T09.md) | T08 | NOT_STARTED | Non ancora implementato |

Gli ID con zero iniziale corrispondono a T1–T9 nella tabella riferimento §15. Non sono task aggiuntivi.

## Regole di avanzamento

- Stati ammessi: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`.
- Una milestone è DONE solo dopo le prove della scheda. Se il codice è scritto ma le prove non sono eseguibili, mantenere IN_PROGRESS/BLOCKED e motivare.
- Avanzamento sequenziale di default. È possibile definire in anticipo contratti di componenti successivi; non dichiararli implementati.
- Componenti economiche future sono disattivate esplicitamente nei profili incrementali, mai sostituite con transazioni gratuite.
- Alla fine del task aggiornare la riga, questo riepilogo iniziale, DECISIONS se necessario e docs/ACCEPTANCE.
- Conservare il dettaglio lungo in un report di task creato al completamento, con percorso riportato nella tabella. Non gonfiare indefinitamente il file caricato a ogni sessione.
- Revisioni economiche T01/T04/T05: verifica del ledger e delle contropartite; non sono richieste automatiche di approvazione dell'utente.

## Evidenze da registrare alla chiusura

Per ogni task registrare data, commit se disponibile, parti implementate, comando esatto di verifica, risultato/exit code, ambiente, limiti, regressioni note e prossimo passo. Non copiare tutto l'output dei test nel piano: collegare il report pertinente.

## Traguardi

- Fondamenta D0: T01 più infrastruttura tecnica iniziale; non dichiarare la demo interattiva pronta.
- Economia integrata da CLI: dopo T05, con le verifiche economiche pertinenti.
- Prima interazione browser reale: dopo T07.
- Primo deliverable D1: solo dopo T08–T09 e matrice di accettazione verificata.

## Vincolo trasversale aggiunto: efficienza NumPy

T01 ha predisposto stato per colonne/ID/RNG e confine ledger. T02 ha verificato kernel batch contro riferimenti scalari e undo del singolo step senza copia dei journal storici. T03–T05 preservano allocazioni e precisione; T06 estende isolamento/checkpoint al runner; T08 misura profiling ed equivalenza. Leggere il modulo performance solo nei task pertinenti.
