# Contratti T06 — runner, HTTP e checkpoint

Versione motore/package **0.6.0**, API HTTP e checkpoint **v1**. Una istanza `RunService` possiede un solo `Runner` attivo. Il worker esegue `Simulation.step()` in un thread seriale; il core rimane indipendente da FastAPI e dall'orologio. Il comando `economic-sim serve --port 8000` avvia un solo processo Uvicorn su `127.0.0.1` con un worker.

## Tempo e comandi

- `PAUSED` alla settimana 0; `step` e `batch` accettati solo in pausa. `run` continua finché arriva `pause`, `ERROR` o `TERMINATED`. `pause` non avvia nuovi step e attende al massimo quello in corso. `speed` imposta 0 < settimane/s ≤ 1000 o `max_speed=true`; non accumula arretrati. `requested_steps_per_second` ed `effective_steps_per_second` sono distinti nello snapshot. La velocità effettiva usa l'intervallo tra avvii successivi, la prima osservazione usa la durata del primo step.
- Ogni mutazione HTTP usa `schema_version: 1`, `command_id` non vuoto e `type`. ID ripetuti nel run restituiscono la risposta originale, conservata anche nel checkpoint. Una nuova simulazione ha nuovo `run_id` e chiude il vecchio worker. Stati incompatibili rispondono 409; input errati 400/422.
- `policy` richiede `submitted_at`, `patch` e opzionalmente `effective_week`. La prima settimana è `t+1` se libera o `t+2` quando `t+1` è già in corso. Le patch persistenti sono ordinate per settimana e sequenza server; per lo stesso parametro/settimana prevale l'ultima accettata. La validazione controlla anche tutte le settimane future dopo la nuova patch. `weekly_bond_purchase_budget` diventa attivo solo alla settimana assegnata.
- `bond_purchase` accetta `budget` e `max_price` in stringhe UM positive. ID diversi nella stessa settimana generano offerte distinte, ciascuna con il proprio limite di prezzo; le quantità assegnate alla BC sono sommate prima del settlement. Non esiste rinvio automatico dell'invenduto.
- Le chiamate HTTP leggono lo snapshot e lo storico pubblicati a fine step. WebSocket invia sequenza monotona, settimana e versione; limita i frame a `max_ui_updates_per_second`, perciò una lacuna di sequenza richiede `GET snapshot` e `GET metrics`. La cronologia e il CSV conservano tutte le settimane. La disconnessione di tutti i browser richiede pausa a confine; la CLI `run` resta autonoma.

## Rotte v1

| Metodo | Rotta | Corpo/risultato |
|---|---|---|
| POST | `/api/runs` | `{schema_version:1, config_path:"configs/t05.yaml"}` → snapshot iniziale |
| GET | `/api/runs/{id}/snapshot` | ultimo snapshot coerente, stato runner, comandi pendenti, `sequence_number` |
| POST | `/api/runs/{id}/commands` | comando tipizzato → conferma con `server_sequence`, `effective_week` |
| GET | `/api/runs/{id}/metrics?from_week=1&to_week=52` | righe settimanali, intervallo inclusivo |
| GET | `/api/runs/{id}/markets/{market_id}` | mercato dell'ultima settimana pubblicata |
| GET | `/api/runs/{id}/agents/{agent_id}?offset=0&limit=50` | colonne, deposito/riserve e transazioni paginate |
| POST | `/api/runs/{id}/checkpoints` | `{schema_version:1,path:"runs/name.json"}` → checksum |
| POST | `/api/runs/import` | `{schema_version:1,path:"runs/name.json"}` → nuovo run in pausa |
| GET | `/api/runs/{id}/export/metrics.csv` | tutte le settimane chiuse |
| WS | `/api/runs/{id}/events` | snapshot/eventi numerati; recupero via HTTP |

Le rotte file ammettono solo YAML in `configs/` e checkpoint JSON in `runs/`, senza uscire da quelle directory. Snapshot, metriche e importi monetari esposti sono copie JSON; le risposte non condividono buffer NumPy mutabili. L'endpoint agente include soltanto persone, imprese e banche; i bilanci istituzionali restano nel ledger e nelle metriche.

## Formato checkpoint

JSON con `checkpoint_version`, `engine_version`, `layout_version`, `economic_checksum`, `checksum`, `state`, `config_ordered`, `orders` e `runtime`. `state` è la proiezione economica canonica del motore: tabelle per colonne, ledger/journal, scorte/journal, contratti, quote, RNG, politiche, aste, crisi, metriche e storia. `config_ordered` e `orders` preservano l'ordine necessario al replay quando il JSON canonico ordina le chiavi. `runtime` contiene log degli ID di comando, sequenza e comandi futuri; resta fuori dal checksum economico. Versione e checksum sono validati prima del ripristino; il nuovo run è in pausa con un nuovo ID. Scrittura su file temporaneo, `fsync` e sostituzione atomica. Nessun thread, socket, lock o pickle serializzato.

Il ledger/registro fisico vengono validati interamente all'import. L'undo del core copia solo lo stato corrente e conserva offset nei journal append-only; lo storico non viene copiato a ogni step. Il checkpoint serializza l'intera storia solo al salvataggio. Il benchmark di throughput e memoria alla scala D1 resta T08.
