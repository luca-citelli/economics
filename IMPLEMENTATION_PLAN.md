# Piano di implementazione D1

Aggiornamento iniziale: 27 settembre 2026. Le specifiche sono pronte; **nessun task software è stato avviato**. Questo è lo stato documentale, non un rapporto di test.

## Ripresa rapida

- Task corrente: nessuno.
- Prossimo task: **T01**.
- Ultimo risultato: pacchetto integrato 3.2: specifiche modulari, nove task, rimandi verificati e decisioni di prodotto esplicite.
- Codice esistente: nessuno.
- Test software eseguiti: nessuno.
- Blocchi noti: nessuno per iniziare T01; le scelte tecniche/calibrazioni residue sono assegnate in DECISIONS.
- Prima azione: leggere la scheda T01 e implementare contratti, configurazione, ledger e inizializzazione.

## Stato delle milestone

| ID | Task | Dipendenze | Stato | Evidenza di completamento |
|---|---|---|---|---|
| T01 | [Contratti e inizializzazione](tasks/T01.md) | Nessuna | NOT_STARTED | Non ancora implementato |
| T02 | [Economia reale](tasks/T02.md) | T01 | NOT_STARTED | Non ancora implementato |
| T03 | [Banche e politica monetaria](tasks/T03.md) | T01–T02 | NOT_STARTED | Non ancora implementato |
| T04 | [Governo e debito](tasks/T04.md) | T03 | NOT_STARTED | Non ancora implementato |
| T05 | [Capitale e crisi](tasks/T05.md) | T02–T04 | NOT_STARTED | Non ancora implementato |
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

T01 predispone stato per colonne/ID/RNG e confine ledger; T02 introduce primi kernel batch; T03–T05 preservano allocazioni e precisione; T06 isola buffer/checkpoint senza copie dello storico; T08 misura profiling ed equivalenza. Leggere il modulo performance solo nei task pertinenti, secondo le schede aggiornate. Nessun task è ancora iniziato.
