# Struttura del repository

Documento normativo corrente (revisione 3.2). Riferimenti storici: §13.3. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

### 13.3 Struttura proposta

```text
economics/
  README.md
  SPEC.md
  IMPLEMENTATION_PLAN.md
  DECISIONS.md
  PROMPTS.md
  docs/
    INDEX.md
    product_scope.md
    model/
    technical/
    archive/
    CORE_RULES.md
    READING_GUIDE.md
    ACCEPTANCE.md
  tasks/
    README.md
    T01.md  # fino a T09.md
  AGENTS.md
  CLAUDE.md
  pyproject.toml
  configs/
    base.yaml
    products.yaml
    scenarios/
  src/economic_sim/
    config.py
    simulation.py
    initialization.py
    accounting/
    agents/
    markets/
    policies/
    metrics/
    persistence/
    random_utils.py
    cli.py
  src/economic_app/
    api.py
    runner.py
    commands.py
    schemas.py
  frontend/
    src/
      api/
      components/
      pages/
      state/
    package.json
  tests/
    accounting/
    markets/
    integration/
    scenarios/
  scripts/
    start.ps1
    start.sh
  runs/
```

Python 3.11+ o versione compatibile fissata; dataclass per contenitori di stato con colonne NumPy e viste leggere degli agenti, Pydantic per configurazioni/API, NumPy per RNG, pandas per analisi/export, pytest per test. TypeScript con controlli statici; test UI/componenti e un percorso end-to-end nel browser. Non introdurre framework ABM aggiuntivi se non risolvono un problema concreto.

`SPEC.md` è una panoramica breve; `docs/INDEX.md` instrada ai moduli normativi in `docs/model/` e `docs/technical/`. Le schede `tasks/T01.md`–`T09.md` descrivono l'implementazione e rimandano ai moduli. `AGENTS.md` e `CLAUDE.md` contengono istruzioni brevi e condivise, senza importare tutta la documentazione. Il piano registra lo stato; DECISIONS registra scelte e motivazioni. Nessuna seconda specifica completa viene mantenuta manualmente.

I kernel numerici possono risiedere in `src/economic_sim/numerics/` e le tabelle di stato in `state/`. Le classi in `agents/` descrivono viste/regole, senza duplicare i saldi o le colonne autorevoli. Struttura finale da dettagliare in T01 secondo [performance_and_vectorization.md](performance_and_vectorization.md).
