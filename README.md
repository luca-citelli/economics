# economics — simulatore economico agent-based

Motore Python e frontend **0.7.0**, 30 settembre 2026, sulla documentazione modulare 3.2.

L'utente interpreta la banca centrale; mercati e agenti formano prezzi, salari e rendimenti. Webapp locale: motore Python indipendente, FastAPI, React/TypeScript/Vite.

## Stato del progetto

**T07 implementato:** webapp React/TypeScript con controlli temporali, pannello BC, mercati distinti, grafici, finanza, agenti paginati, eventi, checkpoint ed export CSV. FastAPI serve la build dalla stessa porta dell'API. `configs/t05.yaml` mantiene l'economia integrata T05. Calibrazione e consegna T08–T09 restano aperte; D1 non è completo.

Il profilo incrementale non è calibrato: nella prova di 52 settimane attività e occupazione calano fortemente, fino a zero consumi finali nell'ultima settimana. Le invarianti restano rispettate; risultati, diagnosi e limiti nel [report T02](docs/reports/T02.md).

## Installazione e uso

Servono Python **3.11.9**, `uv` (verificato **0.7.5**) e, per compilare la UI, Node **24.14.0** con npm **11.9.0** (versioni verificate su Windows). Il progetto accetta Python 3.11 e fissa l'interprete in `.python-version`; `uv.lock` e `frontend/package-lock.json` bloccano le dipendenze. Eseguire dalla radice del repository, in PowerShell su Windows oppure in una shell su macOS/Linux:

```sh
uv --native-tls sync --locked
uv run --locked economic-sim validate configs/base.yaml
uv run --locked economic-sim init configs/base.yaml --output runs/week0.json
uv run --locked economic-sim validate configs/t02.yaml
uv run --locked economic-sim run configs/t02.yaml --steps 52 --csv runs/t02-52.csv --output runs/t02-52.json
uv run --locked economic-sim validate configs/t03.yaml
uv run --locked economic-sim run configs/t03.yaml --steps 52 --csv runs/t03-52.csv --output runs/t03-52.json
uv run --locked economic-sim validate configs/t04.yaml
uv run --locked economic-sim run configs/t04.yaml --steps 53 --csv runs/t04-53.csv --output runs/t04-53.json
uv run --locked economic-sim validate configs/t05.yaml
uv run --locked economic-sim run configs/t05.yaml --steps 52 --csv runs/t05-52.csv --output runs/t05-52.json
uv run --locked economic-sim run configs/t05-investment.yaml --steps 52 --csv runs/t05-investment.csv --output runs/t05-investment.json
uv run --locked economic-sim run configs/t05-crisis.yaml --steps 52 --csv runs/t05-crisis.csv --output runs/t05-crisis.json
uv run --locked economic-sim run configs/t05-bank-crisis.yaml --steps 52 --csv runs/t05-bank-crisis.csv --output runs/t05-bank-crisis.json
uv run --locked pytest -q
uv run --locked economic-sim serve --port 8000
```

Per compilare o aggiornare il frontend prima di `serve`:

```sh
cd frontend
npm ci
npm run build
cd ..
uv run --locked economic-sim serve --port 8000
```

Aprire [http://127.0.0.1:8000/](http://127.0.0.1:8000/) nel browser. Il dev server si avvia con `cd frontend && npm run dev` e usa il proxy `/api` verso FastAPI sulla porta 8000; avviare anche il backend in un altro terminale. Dopo la build, l'uso locale non richiede Internet. La wheel 0.7.0 include gli asset compilati; la prova di installazione pulita resta T09.

`sync` crea `.venv` e installa package e dipendenze di sviluppo, inclusa la libreria WebSocket necessaria a Uvicorn. Su questa macchina `--native-tls` è necessario per usare i certificati di sistema, senza disabilitare la verifica TLS. L'installazione iniziale richiede rete o cache già disponibile; simulatore e UI compilata non usano la rete esterna. I comandi sono stati eseguiti su Windows; macOS/Linux non sono ancora stati collaudati.

`validate` controlla scenario e catalogo; `init` costruisce lo stato reale, verifica le invarianti e salva il riepilogo con aggregati, bilanci, scritture, proprietà e inventari. Gli importi JSON sono stringhe a sei decimali. Senza `--output` il JSON va su stdout; la diagnosi va su stderr. Errori di configurazione restituiscono exit code 2. `runs/` è esclusa da Git. Questo export **non è un checkpoint ricaricabile**.

`run` esegue N settimane sincrone dei profili `real_economy`, `monetary_economy`, `fiscal_economy` e `complete_economy`, verifica le invarianti e scrive il CSV completo. `--output` aggiunge snapshot finale, diagnosi delle imprese, aste azionarie, liquidazioni, mercati fisici e cronologia degli eventi settimanali. Le celle CSV vuote e i `null` JSON indicano metriche non osservate, ad esempio prezzi senza scambi. Un default sovrano o una crisi bancaria irrisolta conclude il run con stato `TERMINATED` ed evento dedicato; un errore software conserva stato `ERROR`. La CLI `run` è autonoma e sincrona; pausa, velocità e import si controllano tramite API.

### Provare l'API locale

Avviare `uv run --locked economic-sim serve --port 8000` in un terminale. Il server ascolta soltanto `127.0.0.1`, con un processo e un worker. In un secondo terminale PowerShell:

```powershell
$run = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/runs' -ContentType 'application/json' -Body '{"schema_version":1,"config_path":"configs/t05-crisis.yaml"}'
$id = $run.run_id
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/runs/$id/commands" -ContentType 'application/json' -Body '{"schema_version":1,"command_id":"step-1","type":"step"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/runs/$id/snapshot"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/runs/$id/metrics?from_week=1"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/runs/$id/checkpoints" -ContentType 'application/json' -Body '{"schema_version":1,"path":"runs/manual.json"}'
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/runs/import' -ContentType 'application/json' -Body '{"schema_version":1,"path":"runs/manual.json"}'
```

Attendere che `snapshot.status` torni `PAUSED` prima di salvare; la conferma del comando indica accettazione, non completamento dello step. `GET .../export/metrics.csv` esporta tutte le settimane chiuse. La UI permette di creare un run con override validati per seed, popolazione e banche. Politiche future comprendono tassi, accesso all'emergenza, cap/haircut delle facilities e budget periodico degli acquisti; la UI separa bozza, pendente e attivo. Schema di base in [contratti T06](docs/technical/t06_contracts.md), estensioni in [report T07](docs/reports/T07.md). Su macOS/Linux gli stessi endpoint funzionano con qualsiasi client HTTP; la riga di avvio è identica. L'avvio su queste piattaforme non è ancora stato verificato.

Gli scenari T05 da 100 persone esercitano rispettivamente la raccolta di quote, i default su prestiti e una crisi bancaria da remunerazione delle riserve estremamente negativa. Quest'ultimo è uno stress contabile stilizzato, non una previsione o un tasso consigliato. I parametri sono nei file YAML e i risultati nelle colonne CSV/eventi JSON.

Altri comandi verificati:

```sh
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv --native-tls build
```

La build produce wheel e archivio sorgente in `dist/`. L'installazione della wheel in un secondo ambiente è stata verificata per T01. La build 0.6.0 è documentata nel [report T06](docs/reports/T06.md).

API Python disponibile:

```python
from economic_sim import Simulation
from economic_sim.config import load_config

simulation = Simulation.from_config(load_config("configs/t02.yaml"))
metrics = simulation.step()
print(metrics["employed"], metrics["primary_satisfaction"])
simulation.export_csv("runs/week1.csv")
simulation.validate()
```

Il profilo T02 ha 1.000 persone, 33 imprese (9 estrattive) e 3 banche. Fiscalità, interessi e spesa sono zero; credito dinamico, Tesoro, aste finanziarie, crisi e dividendi sono no-op espliciti. Il bond ereditato T01 resta congelato come contropartita delle riserve, anche alla settimana 52. Il profilo T04 attiva il servizio di quel bond e ne attraversa la scadenza. Il profilo T05 abilita tutte le fasi economiche. `configs/base.yaml` conserva `initialization_only` e rifiuta `step()`.

Ricette e dotazioni sono una calibrazione proposta. Apertura e controparti nei [contratti T01](docs/technical/t01_contracts.md); algoritmi, parametri, precisione e dizionario metriche nei [contratti T02](docs/technical/t02_contracts.md); formule e priorità di quote/crisi nei [contratti T05](docs/technical/t05_contracts.md).

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

## Prossime milestone

T08–T09 aggiungeranno calibrazione, benchmark di scala e prova di installazione pulita. La prova T06 da 100 settimane non sostituisce il benchmark D1 da 260 settimane o quello di scala.

## Efficienza richiesta

Il progetto prevede già da T01 una struttura adatta a NumPy, non solo una generica promessa di ottimizzazione futura. Dati omogenei per colonne, kernel batch e contabilità separata consentono una migrazione progressiva. Dettagli, precisione e benchmark in [performance_and_vectorization.md](docs/technical/performance_and_vectorization.md).
