# Frontend, architettura e distribuzione

Documento normativo corrente (revisione 3.2). Riferimenti storici: §3. I numeri sono conservati per continuità, non richiedono un documento monolitico. Vedi [indice](../INDEX.md).

## 3. Scelta del frontend e architettura

### 3.1 Locale e webapp non sono alternative incompatibili

Si propone **una webapp locale**: Python esegue il simulatore sul computer dell'utente e il browser visualizza l'interfaccia su `localhost`. Dopo l'installazione delle dipendenze deve poter funzionare senza Internet. Una futura pubblicazione su server deve riutilizzare il motore e gran parte dell'interfaccia.

| Opzione | Vantaggi per questo progetto | Limiti | Decisione |
|---|---|---|---|
| React + FastAPI in locale | Controlli temporali dedicati, schermate ricche, stato del motore separato, evoluzione verso webapp condivisa | Richiede Python e una toolchain frontend durante lo sviluppo | **Scelta proposta** |
| Dashboard Python, ad esempio Streamlit/Dash | Rapida per esplorazioni e validazione del modello | Il ciclo di esecuzione e lo stato della simulazione richiedono comunque cura; per questa UX molti controlli vanno progettati appositamente | Utile per notebook/prototipi accessori |
| Desktop nativo con Qt | Applicazione locale tradizionale e buona integrazione desktop | Interfaccia da adattare sostanzialmente per la distribuzione web | Non prioritario |
| Motore interamente JavaScript nel browser | Distribuzione leggera e nessun backend Python in esecuzione | Cambierebbe il linguaggio del motore e il flusso scientifico previsto | Non scelto |
| Desktop con contenitore web | Riutilizza la UI web e semplifica l'apertura per l'utente | Aggiunge packaging e manutenzione | Eventuale fase successiva |

La scelta è una valutazione di progetto, non un benchmark universale fra framework.

### 3.2 Componenti proposti

- **Core Python:** `Simulation`, agenti, mercati, ledger contabile, inventari, RNG e metriche. Nessuna dipendenza da FastAPI o React.
- **Application service:** possiede la simulazione attiva, serializza comandi, esegue step, salva checkpoint e pubblica snapshot.
- **Backend FastAPI:** REST per comandi/letture e WebSocket per notificare settimane concluse, eventi e stato del runner.
- **Frontend React + TypeScript + Vite:** componenti per tempo, strumenti monetari, grafici, tabelle e dettaglio agenti. Libreria grafici proposta: Recharts.
- **Persistenza D1:** file JSON versionati per checkpoint e comandi, CSV per metriche. SQLite è un'opzione successiva; nessun database server obbligatorio.
- **Calcolo:** un solo worker proprietario dello stato economico e una coda di comandi. Può essere un thread dedicato nel D1; il ciclo CPU non deve bloccare direttamente l'event loop HTTP. Passare a un processo separato solo se misure concrete lo richiedono.

Un solo processo backend e un solo worker economico nel D1: avviare più worker Uvicorn indipendenti creerebbe stati divergenti e DEVE essere escluso dalla configurazione di lancio.

Il backend è l'unica fonte autorevole di settimana, conti, politiche ed esiti. Il browser non ricalcola l'economia. Alla riconnessione rilegge uno snapshot completo e poi riprende gli aggiornamenti.

### 3.3 Distribuzione iniziale

Target iniziale: Windows, con istruzioni riproducibili anche per macOS/Linux.

- Sviluppo: backend e dev server frontend separati, con proxy configurato.
- Uso locale: build frontend servita dallo stesso backend; script di avvio PowerShell e shell.
- Bind di default a `127.0.0.1`; nessun account o cloud richiesto.
- Future installazioni condivise richiederanno autenticazione, isolamento delle sessioni e persistenza server: non sono incluse automaticamente nel D1.
- Versioni compatibili e dipendenze fissate nei lockfile alla creazione del repository.

## Predisposizione numerica richiesta

Lo stato omogeneo degli agenti viene organizzato per colonne NumPy dal T01, con IDs stabili e viste di dominio leggere; il ledger resta fonte esatta dei saldi. Kernel numerici e settlement sono separati. Algoritmi progressivamente vettoriali, stessa semantica economica. Requisiti completi in [performance_and_vectorization.md](performance_and_vectorization.md); questo è un vincolo architetturale, non un'ottimizzazione facoltativa da considerare soltanto dopo aver costruito migliaia di oggetti mutabili indipendenti.
