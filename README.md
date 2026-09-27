# economics — simulatore economico agent-based

Fondamenta Python **0.1.0**, 27 settembre 2026, sulla documentazione modulare 3.2.

L'utente interpreta la banca centrale; mercati e agenti formano prezzi, salari e rendimenti. Webapp locale: motore Python indipendente, FastAPI, React/TypeScript/Vite.

## Stato del progetto

**T01 completato:** package installabile, configurazione rigorosa, catalogo di 11 prodotti, ledger Decimal, settlement e inizializzazione deterministica con stato NumPy per colonne. CLI e test verificano la settimana 0. Non ci sono ancora step economici, API HTTP o frontend; D1 non è completo. Prossimo task: **T02 — Economia reale**. Evidenze e limiti nel [report T01](docs/reports/T01.md).

## Installazione e uso

Servono Python **3.11.9** e `uv` (verificato **0.7.5**). Il progetto accetta Python 3.11 e fissa l'interprete in `.python-version`; `uv.lock` blocca le dipendenze. Non servono Node o servizi esterni per T01. Eseguire dalla radice del repository, in PowerShell su Windows oppure in una shell su macOS/Linux:

```sh
uv --native-tls sync --locked
uv run --locked economic-sim validate configs/base.yaml
uv run --locked economic-sim init configs/base.yaml --output runs/week0.json
uv run --locked pytest -q
```

`sync` crea `.venv` e installa package e dipendenze di sviluppo. Su questa macchina `--native-tls` è necessario per usare i certificati di sistema, senza disabilitare la verifica TLS. L'installazione iniziale richiede rete o cache già disponibile; il core non usa la rete. I comandi sono stati eseguiti su Windows; macOS/Linux non sono ancora stati collaudati.

`validate` controlla scenario e catalogo; `init` costruisce lo stato reale, verifica le invarianti e salva il riepilogo con aggregati, bilanci, scritture, proprietà e inventari. Gli importi JSON sono stringhe a sei decimali. Senza `--output` il JSON va su stdout; la diagnosi va su stderr. Errori di configurazione restituiscono exit code 2. `runs/` è esclusa da Git. Questo export **non è un checkpoint ricaricabile**.

Altri comandi verificati:

```sh
uv run --locked ruff check src tests
uv run --locked ruff format --check src tests
uv --native-tls build
```

La build produce wheel e archivio sorgente in `dist/`. È stata verificata anche un'installazione della wheel in un secondo ambiente, con dipendenze esportate da `uv.lock`, e l'inizializzazione fuori dalla directory sorgente. Dettagli nel report T01.

API Python disponibile:

```python
from economic_sim import Simulation
from economic_sim.config import load_config

simulation = Simulation.from_config(load_config("configs/base.yaml"))
simulation.validate()
print(simulation.snapshot().model_dump_json(indent=2))
```

Il caso base ha 1.000 persone, 33 imprese (9 estrattive) e 3 banche. Ogni fase futura è esplicitamente disattivata nel profilo `initialization_only`; non esiste ancora `step()`. Ricette, dotazioni e prezzi sono una calibrazione proposta. Formule, controparti di apertura, dtype, RNG e schemi sono descritti nei [contratti T01](docs/technical/t01_contracts.md).

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

T02 introduce lavoro, produzione e mercati reali; T03–T05 credito, Tesoro, investimenti e crisi; T06 il runner/backend; T07 il frontend; T08–T09 calibrazione e consegna. Nessuna esecuzione di 260 settimane o misura prestazionale viene dichiarata da T01.

## Efficienza richiesta

Il progetto prevede già da T01 una struttura adatta a NumPy, non solo una generica promessa di ottimizzazione futura. Dati omogenei per colonne, kernel batch e contabilità separata consentono una migrazione progressiva. Dettagli, precisione e benchmark in [performance_and_vectorization.md](docs/technical/performance_and_vectorization.md).
