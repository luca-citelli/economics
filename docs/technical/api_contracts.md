# Contratti Python e HTTP

Documento normativo corrente (revisione 3.2). Riferimenti storici: §13.1–13.2. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 13.1 API Python del motore

**Stato dopo T06:** `load_config`, `Simulation.from_config`, `validate`, `snapshot`, `step` ed export CSV sono eseguibili. Il runner programma politiche e gestisce checkpoint tramite `Runner`, `save_checkpoint` e `load_checkpoint`; l'esempio Python seguente mostra il percorso sincrono. Le API interattive effettive sono nei [contratti T06](t06_contracts.md) e nel README.

```python
config = load_config("configs/t05.yaml")
sim = Simulation.from_config(config)
for _ in range(52):
    sim.step()
    if sim.status == "TERMINATED":
        break
sim.export_csv("runs/example/metrics.csv")
```

`step()` non include sleep né dipende dal browser. Il runner gestisce la velocità. `snapshot()` contiene `run_id`, `week`, `state_version`, metriche, mercati, eventi e checksum dello stato economico canonico.

### 13.2 API HTTP implementata in T06

| Metodo/percorso | Funzione |
|---|---|
| `POST /api/runs` | Crea simulazione da scenario/configurazione validata |
| `GET /api/runs/{id}/snapshot` | Ultimo stato coerente e politiche pendenti |
| `POST /api/runs/{id}/commands` | Step, batch, run, pause, speed, policy; corpo tipizzato e `command_id` |
| `GET /api/runs/{id}/metrics?from_week=&to_week=` | Storico completo nell'intervallo |
| `GET /api/runs/{id}/event-history` | Eventi economici per settimana conclusa |
| `GET /api/runs/{id}/markets/{market_id}` | Offerte, scambi, quantità e prezzi aggregati |
| `GET /api/runs/{id}/agents/{agent_id}` | Stato, bilancio e transazioni paginate |
| `POST /api/runs/{id}/checkpoints` | Salvataggio a confine di step |
| `POST /api/runs/import` | Caricamento validato in nuovo run in pausa |
| `GET /api/runs/{id}/export/metrics.csv` | Export storico |
| `WS /api/runs/{id}/events` | Snapshot/eventi numerati, stato runner, conferme |

Il comando accettato non equivale a operazione completata: risposta con `command_id`, stato e settimana assegnata, poi conferma di esecuzione. API versionate; errori di validazione, conflitti e guasti distinguibili.

Corpi JSON, limiti, stato runner, path locali e formato checkpoint di base sono definiti nei [contratti T06](t06_contracts.md). T07 aggiunge a `POST /api/runs` gli override validati `seed`, `initial_population`, `initial_banks`; alla patch `policy` aggiunge `emergency_lending_enabled`, `facility_cap_share`, `ordinary_haircut` e `emergency_haircut`. Lo snapshot del runner espone `central_bank_controls` attivi, parametri dei `pending_commands`, `decision_history` e `inventories` per prodotto. La conferma del comando rimane distinta dall'applicazione alla settimana assegnata. Evidenze nel [report T07](../reports/T07.md).

WebSocket usa `sequence_number`, `week`, `state_version`; dopo una lacuna il client recupera uno snapshot e lo storico necessario via HTTP. Il server può accorpare notifiche ma non perdere dati economici persistiti. Grafici e dettagli non devono essere richiesti per tutti gli agenti a ogni frame.
