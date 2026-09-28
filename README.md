# economics — simulatore economico agent-based

Motore Python **0.3.0**, 28 settembre 2026, sulla documentazione modulare 3.2.

L'utente interpreta la banca centrale; mercati e agenti formano prezzi, salari e rendimenti. Webapp locale: motore Python indipendente, FastAPI, React/TypeScript/Vite.

## Stato del progetto

**T03 completato:** al ciclo reale si aggiungono credito rolling, scoring batch, limiti prudenziali, interessi, corridoio e programmazione dei tassi, facilities garantite e metriche monetarie separate. Il profilo `configs/t03.yaml` è eseguibile dalla CLI. Non ci sono API HTTP o frontend; D1 non è completo. Prossimo task: **T04 — Governo e debito**.

Il profilo incrementale non è calibrato: nella prova di 52 settimane attività e occupazione calano fortemente, fino a zero consumi finali nell'ultima settimana. Le invarianti restano rispettate; risultati, diagnosi e limiti nel [report T02](docs/reports/T02.md).

## Installazione e uso

Servono Python **3.11.9** e `uv` (verificato **0.7.5**). Il progetto accetta Python 3.11 e fissa l'interprete in `.python-version`; `uv.lock` blocca le dipendenze. Non servono Node o servizi esterni per T02. Eseguire dalla radice del repository, in PowerShell su Windows oppure in una shell su macOS/Linux:

```sh
uv --native-tls sync --locked
uv run --locked economic-sim validate configs/base.yaml
uv run --locked economic-sim init configs/base.yaml --output runs/week0.json
uv run --locked economic-sim validate configs/t02.yaml
uv run --locked economic-sim run configs/t02.yaml --steps 52 --csv runs/t02-52.csv --output runs/t02-52.json
uv run --locked economic-sim validate configs/t03.yaml
uv run --locked economic-sim run configs/t03.yaml --steps 52 --csv runs/t03-52.csv --output runs/t03-52.json
uv run --locked pytest -q
```

`sync` crea `.venv` e installa package e dipendenze di sviluppo. Su questa macchina `--native-tls` è necessario per usare i certificati di sistema, senza disabilitare la verifica TLS. L'installazione iniziale richiede rete o cache già disponibile; il core non usa la rete. I comandi sono stati eseguiti su Windows; macOS/Linux non sono ancora stati collaudati.

`validate` controlla scenario e catalogo; `init` costruisce lo stato reale, verifica le invarianti e salva il riepilogo con aggregati, bilanci, scritture, proprietà e inventari. Gli importi JSON sono stringhe a sei decimali. Senza `--output` il JSON va su stdout; la diagnosi va su stderr. Errori di configurazione restituiscono exit code 2. `runs/` è esclusa da Git. Questo export **non è un checkpoint ricaricabile**.

`run` esegue N settimane sincrone dei profili `real_economy` e `monetary_economy`, verifica le invarianti e scrive il CSV completo. `--output` è facoltativo e aggiunge snapshot finale e diagnostica delle imprese. Le celle CSV vuote e i `null` JSON indicano metriche non osservate, ad esempio prezzi senza scambi. La CLI non implementa ancora pausa/velocità o ripresa da checkpoint.

Altri comandi verificati:

```sh
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv --native-tls build
```

La build 0.3.0 produce wheel e archivio sorgente in `dist/`. L'installazione della wheel in un secondo ambiente è stata verificata per T01; non è stata ripetuta per T02. Dettagli nei rispettivi report.

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

Il profilo T02 ha 1.000 persone, 33 imprese (9 estrattive) e 3 banche. Fiscalità, interessi e spesa sono zero; credito dinamico, Tesoro, aste finanziarie, crisi e dividendi sono no-op espliciti. Il bond ereditato T01 resta congelato come contropartita delle riserve, anche alla settimana 52. `configs/base.yaml` conserva invece `initialization_only` e rifiuta `step()`.

Ricette e dotazioni sono una calibrazione proposta. Apertura e controparti nei [contratti T01](docs/technical/t01_contracts.md); algoritmi, parametri, precisione e dizionario metriche nei [contratti T02](docs/technical/t02_contracts.md).

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

T03–T05 aggiungeranno credito, Tesoro, emissioni, distribuzioni e crisi; T06 il runner/backend; T07 il frontend; T08–T09 calibrazione e consegna. La prova T02 da 52 settimane non sostituisce il benchmark D1 da 260 settimane o quello di scala.

## Efficienza richiesta

Il progetto prevede già da T01 una struttura adatta a NumPy, non solo una generica promessa di ottimizzazione futura. Dati omogenei per colonne, kernel batch e contabilità separata consentono una migrazione progressiva. Dettagli, precisione e benchmark in [performance_and_vectorization.md](docs/technical/performance_and_vectorization.md).
