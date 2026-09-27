# Contratti Python e HTTP

Documento normativo corrente (revisione 3.2). Riferimenti storici: §13.1–13.2. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 13.1 API Python del motore

**Stato dopo T01:** sono eseguibili `load_config`, `Simulation.from_config`, `validate`, `snapshot` e la CLI di apertura. Contratti minimi in `src/economic_sim/contracts.py`, dettagli nei [contratti T01](t01_contracts.md). L'esempio completo seguente è il traguardo delle milestone successive: step, politiche, checkpoint ed export temporali non sono ancora implementati.

```python
config = load_config("configs/base.yaml")
sim = Simulation.from_config(config)
sim.schedule_policy(command_id="rate-001", effective_week=10,
                    patch={"policy_rate": 0.04})
for _ in range(52):
    result = sim.step()
    if result.terminated:
        break
sim.save_checkpoint("runs/example/checkpoint.json")
sim.export_metrics_csv("runs/example/metrics.csv")
```

`step()` non include sleep né dipende dal browser. Il runner gestisce la velocità. Ogni risultato contiene almeno `run_id`, `week`, `state_version`, metriche, riepiloghi dei mercati, eventi e checksum dello stato economico canonico.

### 13.2 API HTTP proposta

| Metodo/percorso | Funzione |
|---|---|
| `POST /api/runs` | Crea simulazione da scenario/configurazione validata |
| `GET /api/runs/{id}/snapshot` | Ultimo stato coerente e politiche pendenti |
| `POST /api/runs/{id}/commands` | Step, batch, run, pause, speed, policy; corpo tipizzato e `command_id` |
| `GET /api/runs/{id}/metrics?from_week=&to_week=` | Storico completo nell'intervallo |
| `GET /api/runs/{id}/markets/{market_id}` | Offerte, scambi, quantità e prezzi aggregati |
| `GET /api/runs/{id}/agents/{agent_id}` | Stato, bilancio e transazioni paginate |
| `POST /api/runs/{id}/checkpoints` | Salvataggio a confine di step |
| `POST /api/runs/import` | Caricamento validato in nuovo run in pausa |
| `GET /api/runs/{id}/export/metrics.csv` | Export storico |
| `WS /api/runs/{id}/events` | Snapshot/eventi numerati, stato runner, conferme |

Il comando accettato non equivale a operazione completata: risposta con `command_id`, stato e settimana assegnata, poi conferma di esecuzione. API versionate; errori di validazione, conflitti e guasti distinguibili.

WebSocket usa `sequence_number`, `week`, `state_version`; dopo una lacuna il client recupera uno snapshot e lo storico necessario via HTTP. Il server può accorpare notifiche ma non perdere dati economici persistiti. Grafici e dettagli non devono essere richiesti per tutti gli agenti a ogni frame.
